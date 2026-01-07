from __future__ import annotations

import ast
import base64
import datetime
import re
import warnings
from typing import TYPE_CHECKING, Any, ClassVar, Final, cast

import haystack
from django.conf import settings
from django.contrib.gis.measure import Distance
from django.core.exceptions import ImproperlyConfigured
from haystack import connections
from haystack.backends import (
    BaseEngine,
    BaseSearchBackend,
    BaseSearchQuery,
    UnifiedIndex,
    log_query,
)
from haystack.constants import DEFAULT_OPERATOR, DJANGO_CT, DJANGO_ID, FUZZINESS, ID
from haystack.exceptions import SkipDocument
from haystack.inputs import Clean, Exact, PythonData, Raw
from haystack.models import SearchResult
from haystack.utils import get_identifier, get_model_ct
from haystack.utils import log as logging
from haystack.utils.app_loading import haystack_get_model
from haystack.utils.geo import generate_bounding_box
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError, TransportError
from opensearchpy.helpers import bulk, scan

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from django.db.models import Model


# Regex pattern for parsing datetime strings from OpenSearch
DATETIME_REGEX: Final[re.Pattern[str]] = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T"
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(?:\.(?P<microsecond>\d+))?$"
)


class OpenSearchSearchBackend(BaseSearchBackend):
    """
    OpenSearch backend for django-haystack using opensearch-py.

    This backend is compatible with OpenSearch 3.3 and maintains API compatibility
    with the elasticsearch7_backend while using opensearch-py instead of elasticsearch.
    """

    # Word reserved by OpenSearch for special use.
    RESERVED_WORDS = ("AND", "NOT", "OR", "TO")

    # Characters reserved by OpenSearch for special use.
    # The '\\' must come first, so as not to overwrite the other slash replacements.
    RESERVED_CHARACTERS = (
        "\\",
        "+",
        "-",
        "&&",
        "||",
        "!",
        "(",
        ")",
        "{",
        "}",
        "[",
        "]",
        "^",
        '"',
        "~",
        "*",
        "?",
        ":",
        "/",
    )

    # Settings to add an n-gram & edge n-gram analyzer.
    DEFAULT_SETTINGS: ClassVar[dict[str, Any]] = {
        "settings": {
            "index": {
                "max_ngram_diff": 2,
            },
            "analysis": {
                "analyzer": {
                    "ngram_analyzer": {
                        "tokenizer": "standard",
                        "filter": [
                            "haystack_ngram",
                            "lowercase",
                        ],
                    },
                    "edgengram_analyzer": {
                        "tokenizer": "standard",
                        "filter": [
                            "haystack_edgengram",
                            "lowercase",
                        ],
                    },
                },
                "filter": {
                    "haystack_ngram": {
                        "type": "ngram",
                        "min_gram": 3,
                        "max_gram": 4,
                    },
                    "haystack_edgengram": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 15,
                    },
                },
            },
        },
    }

    #: The default field mapping for text fields.
    DEFAULT_FIELD_MAPPING: ClassVar[dict[str, Any]] = {
        "type": "text",
        "analyzer": "snowball",
    }

    #: The field mappings for the index.
    FIELD_MAPPINGS: ClassVar[dict[str, Any]] = {
        "edge_ngram": {
            "type": "text",
            "analyzer": "edgengram_analyzer",
        },
        "ngram": {
            "type": "text",
            "analyzer": "ngram_analyzer",
        },
        "date": {"type": "date"},
        "datetime": {"type": "date"},
        "location": {"type": "geo_point"},
        "boolean": {"type": "boolean"},
        "float": {"type": "float"},
        "long": {"type": "long"},
        "integer": {"type": "long"},
    }

    def __init__(self, connection_alias: str, **connection_options: Any):
        """
        Initialize OpenSearch backend with opensearch-py client.

        Args:
            connection_alias: The alias of the connection.
            **connection_options: The connection options.

        """
        super().__init__(connection_alias, **connection_options)

        if "URL" not in connection_options:
            msg = (
                "You must specify a 'URL' in your settings for connection "
                f"'{connection_alias}'."
            )
            raise ImproperlyConfigured(msg)

        if "INDEX_NAME" not in connection_options:
            msg = (
                "You must specify a 'INDEX_NAME' in your settings for connection "
                f"'{connection_alias}'."
            )
            raise ImproperlyConfigured(msg)

        # opensearch-py expects hosts as a list or single host string
        url = connection_options["URL"]
        hosts = [url] if isinstance(url, str) else url
        self.conn = OpenSearch(
            hosts=hosts,
            timeout=self.timeout,
            **connection_options.get("KWARGS", {}),
        )
        self.index_name: str = connection_options["INDEX_NAME"]
        self.log: logging.Logger = logging.getLogger("haystack")
        self.setup_complete: bool = False
        self.existing_mapping: dict[str, Any] = {}
        self.content_field_name: str | None = None

    def _get_doc_type_option(self):
        """
        OpenSearch 3.3 does not support a doc_type option.

        Returns:
            An empty dictionary.

        """
        return {}

    def _get_current_mapping(self, field_mapping: dict[str, Any]) -> dict[str, Any]:
        """
        OpenSearch 3.3 does not support a doc_type option.

        Args:
            field_mapping: The field mapping to get the current mapping for.

        Returns:
            A dictionary with the properties of the field mapping.

        """
        return {"properties": field_mapping}

    def _add_keyword_and_exact_subfields(
        self,
        props: dict[str, Any],
        unified_index: UnifiedIndex,  # noqa: ARG002
    ) -> dict[str, Any]:
        """
        Modify generated properties so that:

          * Text fields get a `.keyword` subfield for exact matching and faceting

        Args:
           props: The field mapping to add the keyword subfields to.
           unified_index: The unified index.

        Returns:
           A dictionary with the properties of the field mapping with the
           keyword subfields added.

        """
        new_props: dict[str, Any] = {}

        for field, definition in props.items():
            # Always copy base definition
            new_props[field] = definition

            # If field is text type, add a keyword subfield
            if definition.get("type") == "text":
                new_props[field] = {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                }

        return new_props

    def setup(self) -> None:
        """
        Setup the index and mappings.

        Raises:
            TransportError: If the index creation or mapping update fails.

        """
        try:
            mapping_response: dict[str, Any] = self.conn.indices.get_mapping(
                index=self.index_name
            )
            if self.index_name in mapping_response:
                self.existing_mapping = mapping_response[self.index_name].get(
                    "mappings", {}
                )
            else:
                self.existing_mapping = {}
        except NotFoundError:
            self.existing_mapping = {}
        except TransportError:
            if not self.silently_fail:
                raise
            self.existing_mapping = {}

        unified_index = haystack.connections[self.connection_alias].get_unified_index()
        self.content_field_name, field_mapping = self.build_schema(
            unified_index.all_searchfields()
        )
        field_mapping = self._add_keyword_and_exact_subfields(
            field_mapping, unified_index
        )

        current_mapping = self._get_current_mapping(field_mapping)

        if current_mapping != self.existing_mapping:
            try:
                self.conn.indices.create(
                    index=self.index_name, body=self.DEFAULT_SETTINGS, ignore=[400]
                )
                self.conn.indices.put_mapping(
                    index=self.index_name,
                    body=current_mapping,
                )
                self.existing_mapping = current_mapping
            except TransportError:
                if not self.silently_fail:
                    raise

        self.setup_complete = True

    def _iso_datetime(self, value: Any) -> str | None:
        """
        If value appears to be something datetime-like, return it in ISO format.

        Otherwise, return None.
        """
        if hasattr(value, "strftime"):
            if hasattr(value, "hour"):
                return value.isoformat()
            # date objects have strftime but not hour
            if hasattr(value, "isoformat"):
                return f"{value.isoformat()}T00:00:00"
        return None

    def _from_python(self, value):
        """Convert more Python data types to OpenSearch-understandable JSON."""
        iso = self._iso_datetime(value)
        if iso:
            return iso
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, bytes):
            # TODO: Be stricter.
            return str(value, errors="replace")
        if isinstance(value, set):
            return list(value)
        return value

    def _to_python(self, value: Any):
        """Convert values from OpenSearch to native Python values."""
        if isinstance(value, (int, float, list, tuple, bool)):
            return value

        if isinstance(value, str):
            possible_datetime = DATETIME_REGEX.search(value)

            if possible_datetime:
                date_values = possible_datetime.groupdict()

                for dk, dv in date_values.items():
                    if dk == "microsecond" and dv:
                        # Convert to microseconds (e.g., .123 -> 123000)
                        date_values[dk] = int(dv.ljust(6, "0")[:6])
                    elif dv:
                        date_values[dk] = int(dv)
                    else:
                        date_values[dk] = 0

                return datetime.datetime(
                    year=date_values["year"],
                    month=date_values["month"],
                    day=date_values["day"],
                    hour=date_values["hour"],
                    minute=date_values["minute"],
                    second=date_values["second"],
                    microsecond=date_values["microsecond"],
                    tzinfo=datetime.timezone.utc,
                )

        try:
            # This is slightly gross but it's hard to tell otherwise what the
            # string's original type might have been. Be careful who you trust.
            converted_value = ast.literal_eval(value)

            # Try to handle most built-in types.
            if isinstance(converted_value, (int, list, tuple, set, dict, float)):
                return converted_value
        except (ValueError, SyntaxError):
            pass

        return value

    def _prepare_object(self, index, obj):
        """Prepare objects for indexing."""
        return index.full_prepare(obj)

    def _prepare_documents_for_bulk(
        self, index: str, iterable: Iterable[Any]
    ) -> list[dict[str, Any]]:
        """
        Prepare documents for bulk indexing.

        Args:
            index: The index to prepare the documents for.
            iterable: The iterable of objects to prepare.

        Returns:
            A list of prepared documents.

        Raises:
            TransportError: If the document preparation fails.
            SkipDocument: If the document is skipped.
            Exception: If an unexpected error occurs.

        """
        prepped_docs = []
        for obj in iterable:
            try:
                prepped_data = self._prepare_object(index, obj)
                final_data = {}

                for key, value in prepped_data.items():
                    final_data[key] = self._from_python(value)

                final_data["_index"] = self.index_name
                final_data["_id"] = final_data[ID]

                prepped_docs.append(final_data)
            except SkipDocument:  # noqa: PERF203
                self.log.debug("Indexing for object `%s` skipped", obj)
            except TransportError:
                if not self.silently_fail:
                    raise

                try:
                    obj_id = get_identifier(obj)
                except (AttributeError, TypeError):
                    obj_id = str(obj)

                self.log.exception(
                    "Preparing object for update",
                    extra={"data": {"index": index, "object": obj_id}},
                )

        return prepped_docs

    def get_facet_fieldname(self, field_name: str) -> str:
        """
        Return the correct backend field name for faceting/filtering.

        For text fields, this returns the '.keyword' subfield.
        For other fields, it returns the field name itself.

        Args:
            field_name: The field name to get the facet fieldname for.

        Returns:
            The backend field name for faceting.

        """
        unified_index = haystack.connections[self.connection_alias].get_unified_index()
        for model in unified_index.get_indexed_models():
            index = unified_index.get_index(model)
            if field_name in index.fields:
                if index.fields[field_name].field_type in ("text", "char"):
                    return f"{field_name}.keyword"
                break
        return field_name

    def update(self, index: str, iterable: Iterable[Any], commit: bool = True) -> None:
        """
        Update the backend with documents from the given SearchIndex.

        Args:
            index: The index to update.
            iterable: The iterable of objects to update.
            commit: Whether to commit the changes.

        Raises:
            TransportError: If the update fails.
            Exception: If an unexpected error occurs.

        """
        if not self.setup_complete:
            try:
                self.setup()
            except TransportError:
                if not self.silently_fail:
                    raise

                self.log.exception("Failed to add documents to OpenSearch")
                return

        prepped_docs = self._prepare_documents_for_bulk(index, iterable)

        if prepped_docs:
            try:
                bulk(self.conn, prepped_docs)
            except TransportError:
                if not self.silently_fail:
                    raise
                self.log.exception("Failed to bulk index documents to OpenSearch")

        if commit:
            try:
                self.conn.indices.refresh(index=self.index_name)
            except TransportError:
                if not self.silently_fail:
                    raise

    def remove(self, obj_or_string: Any, commit: bool = True) -> None:
        """
        Remove a document from the index.

        Args:
            obj_or_string: The object or string to remove.
            commit: Whether to commit the changes.

        Raises:
            TransportError: If the removal fails.

        """
        doc_id = get_identifier(obj_or_string)

        if not self.setup_complete:
            try:
                self.setup()
            except TransportError:
                if not self.silently_fail:
                    raise

                self.log.exception(
                    "Failed to remove document '%s' from OpenSearch",
                    doc_id,
                )
                return

        try:
            self.conn.delete(
                index=self.index_name,
                id=doc_id,
                ignore=[404],
            )

            if commit:
                self.conn.indices.refresh(index=self.index_name)
        except TransportError:
            if not self.silently_fail:
                raise

            self.log.exception(
                "Failed to remove document '%s' from OpenSearch",
                doc_id,
            )

    def _clear_all_models(self) -> None:
        """
        Clear all documents by deleting the index.

        Raises:
            TransportError: If the index deletion fails.

        """
        try:
            self.conn.indices.delete(index=self.index_name, ignore=[404])
            self.setup_complete = False
            self.existing_mapping = {}
            self.content_field_name = None
        except TransportError:
            if not self.silently_fail:
                raise
            self.log.exception("Failed to clear OpenSearch index")

    def _clear_specific_models(self, models: Iterable[Any]) -> None:
        """
        Clear documents for specific models using scroll API.

        Args:
            models: The models to clear.

        Raises:
            TransportError: If the index deletion fails.

        """
        models_to_delete = [f"{DJANGO_CT}:{get_model_ct(model)}" for model in models]
        query: dict[str, Any] = {
            "query": {"query_string": {"query": " OR ".join(models_to_delete)}},
        }
        generator = scan(
            self.conn,
            query=query,
            index=self.index_name,
        )
        actions = ({"_op_type": "delete", "_id": doc["_id"]} for doc in generator)
        bulk(
            self.conn,
            actions=actions,
            index=self.index_name,
        )
        self.conn.indices.refresh(index=self.index_name)

    def clear(
        self,
        models: Iterable[Any] | None = None,
        commit: bool = True,  # noqa: ARG002
    ) -> None:
        """
        Clears the backend of all documents/objects for a collection of models.

        Args:
            models: The models to clear.
            commit: Whether to commit the changes.

        Raises:
            TransportError: If the index deletion fails.

        """
        if models is not None:
            assert isinstance(models, (list, tuple))  # noqa: S101

        try:
            if models is None:
                self._clear_all_models()
            else:
                self._clear_specific_models(models)
        except TransportError:
            if not self.silently_fail:
                raise

            if models is not None:
                models_to_delete: list[str] = [
                    f"{DJANGO_CT}:{get_model_ct(model)}" for model in models
                ]
                self.log.exception(
                    "Failed to clear OpenSearch index of models '%s'",
                    ",".join(models_to_delete),
                )
            else:
                self.log.exception("Failed to clear OpenSearch index")

    def _build_query_string(
        self, query_string: str, content_field: str
    ) -> dict[str, Any]:
        """
        Build the query string portion of search kwargs.

        Args:
            query_string: The query string to build the query string for.
            content_field: The content field to build the query string for.

        Returns:
            A dictionary with the query string portion of search kwargs.

        """
        if query_string == "*:*":
            return {"query": {"match_all": {}}}
        return {
            "query": {
                "query_string": {
                    "default_field": content_field,
                    "default_operator": DEFAULT_OPERATOR,
                    "query": query_string,
                    "analyze_wildcard": True,
                    "fuzziness": FUZZINESS,
                }
            }
        }

    def _add_fields_to_kwargs(
        self, kwargs: dict[str, Any], fields: str | list[str] | set[str]
    ) -> None:
        """
        Add stored_fields to search kwargs.

        Args:
            kwargs: The search kwargs to add the stored_fields to.
            fields: The fields to add to the stored_fields.

        """
        if fields:
            if isinstance(fields, (list, set)):
                fields = " ".join(fields)
            kwargs["stored_fields"] = fields

    def _get_backend_sort_field(self, field: str) -> str:
        """
        Get the backend field name for sorting.

        Args:
            field: The field name to get the backend sort field for.

        Returns:
            The backend sort field name.

        """
        return self.get_facet_fieldname(field)

    def _add_sort_to_kwargs(
        self,
        kwargs: dict[str, Any],
        sort_by: list[str | tuple[str, str]] | None,
        distance_point: dict[str, Any] | None,
    ) -> None:
        """
        Add sort configuration to search kwargs.

        Args:
            kwargs: The search kwargs to add the sort to.
            sort_by: The sort by configuration.
            distance_point: The distance point to add the sort to.

        Raises:
            Warning: If the distance field is used without calling the
                '.distance(...)' method.

        """
        if sort_by is None:
            return

        self.log.info("Adding sort to kwargs: %s", sort_by)
        order_list = []

        for sort_field in sort_by:
            if isinstance(sort_field, str):
                if sort_field.startswith("-"):
                    direction = "desc"
                    field = sort_field[1:]
                else:
                    direction = "asc"
                    field = sort_field
            else:
                field, direction = sort_field

            if field == "distance" and distance_point:
                lng, lat = distance_point["point"].coords
                sort_kwargs = {
                    "_geo_distance": {
                        distance_point["field"]: [lng, lat],
                        "order": direction,
                        "unit": "km",
                    }
                }
            else:
                if field == "distance":
                    warnings.warn(
                        "In order to sort by distance, you must call the "
                        "'.distance(...)' method.",
                        stacklevel=2,
                    )

                backend_field = self._get_backend_sort_field(field)
                sort_kwargs = {backend_field: {"order": direction}}

            order_list.append(sort_kwargs)

        kwargs["sort"] = order_list

    def _add_highlight_to_kwargs(
        self, kwargs: dict[str, Any], highlight: bool, content_field: str
    ) -> None:
        """
        Add highlight configuration to search kwargs.

        Args:
            kwargs: The search kwargs to add the highlight to.
            highlight: The highlight configuration.
            content_field: The content field to add the highlight to.

        Raises:
            Warning: If the distance field is used without calling the
                '.distance(...)' method.

        """
        if not highlight:
            return

        kwargs["highlight"] = {"fields": {content_field: {}}}
        if isinstance(highlight, dict):
            kwargs["highlight"].update(highlight)

    def _add_suggest_to_kwargs(
        self,
        kwargs: dict[str, Any],
        query_string: str,
        spelling_query: str | None,
        content_field: str,
        unified_index: UnifiedIndex,
    ) -> None:
        """
        Add suggest configuration to search kwargs.

        Args:
            kwargs: The search kwargs to add the suggest to.
            query_string: The query string to add the suggest to.
            spelling_query: The spelling query to add the suggest to.
            content_field: The default content field to use for suggestions.
            unified_index: The unified index to check for a dedicated spelling field.

        """
        if not self.include_spelling:
            return

        # Check for a dedicated _spelling field in any of the indexed models
        suggest_field = content_field
        for model in unified_index.get_indexed_models():
            index = unified_index.get_index(model)
            if "_spelling" in index.fields:
                suggest_field = "_spelling"
                break

        kwargs["suggest"] = {
            "suggest": {
                "text": spelling_query or query_string,
                "term": {
                    "field": suggest_field,
                },
            }
        }

    def _add_facets_to_kwargs(
        self, kwargs: dict[str, Any], facets: dict[str, Any] | None
    ) -> None:
        """
        Add facets/aggregations to search kwargs.

        Args:
            kwargs: The search kwargs to add the facets to.
            facets: The facets to add to the search kwargs.

        """
        if facets is None:
            return

        kwargs.setdefault("aggs", {})
        for facet_fieldname, extra_options in facets.items():
            facet_options: dict[str, Any] = {
                "meta": {"_type": "terms"},
                "terms": {"field": self.get_facet_fieldname(facet_fieldname)},
            }
            if "order" in extra_options:
                facet_options["meta"]["order"] = extra_options.pop("order")
            if extra_options.pop("global_scope", False):
                facet_options["global"] = True
            if "facet_filter" in extra_options:
                facet_options["facet_filter"] = extra_options.pop("facet_filter")
            facet_options["terms"].update(extra_options)
            kwargs["aggs"][facet_fieldname] = facet_options

    def _add_date_facets_to_kwargs(
        self, kwargs: dict[str, Any], date_facets: dict[str, Any] | None
    ) -> None:
        """
        Add date facets/aggregations to search kwargs.

        Args:
            kwargs: The search kwargs to add the date facets to.
            date_facets: The date facets to add to the search kwargs.

        """
        if date_facets is None:
            return

        kwargs.setdefault("aggs", {})
        for facet_fieldname, value in date_facets.items():
            interval = value.get("gap_by").lower()
            if value.get("gap_amount", 1) != 1 and interval not in (
                "month",
                "year",
            ):
                interval = f"{value['gap_amount']}{interval[:1]}"

            kwargs["aggs"][facet_fieldname] = {
                "meta": {"_type": "date_histogram"},
                "date_histogram": {"field": facet_fieldname, "interval": interval},
                "aggs": {
                    facet_fieldname: {
                        "date_range": {
                            "field": facet_fieldname,
                            "ranges": [
                                {
                                    "from": self._from_python(value.get("start_date")),
                                    "to": self._from_python(value.get("end_date")),
                                }
                            ],
                        }
                    }
                },
            }

    def _add_query_facets_to_kwargs(
        self, kwargs: dict[str, Any], query_facets: list[tuple[str, str]] | None
    ) -> None:
        """
        Add query facets/aggregations to search kwargs.

        Args:
            kwargs: The search kwargs to add the query facets to.
            query_facets: The query facets to add to the search kwargs.

        """
        if query_facets is None:
            return

        kwargs.setdefault("aggs", {})
        for facet_fieldname, value in query_facets:
            kwargs["aggs"][facet_fieldname] = {
                "meta": {"_type": "query"},
                "filter": {"query_string": {"query": value}},
            }

    def _add_model_filters_to_kwargs(
        self,
        kwargs: dict[str, Any],
        models: Collection[Model] | None,
        limit_to_registered_models: bool | None,
    ) -> list[str]:
        """
        Add model filters to search kwargs.

        Args:
            kwargs: The search kwargs to add the model filters to.
            models: The models to add the model filters to.
            limit_to_registered_models: Whether to limit the models to
              registered models.

        Returns:
            A list of model choices.

        """
        if limit_to_registered_models is None:
            limit_to_registered_models = getattr(
                settings, "HAYSTACK_LIMIT_TO_REGISTERED_MODELS", True
            )

        if models and len(models):
            model_choices = sorted(get_model_ct(model) for model in models)
        elif limit_to_registered_models:
            model_choices = self.build_models_list()
        else:
            model_choices = []

        # Now actually add the model filter to kwargs if any models exist.
        if model_choices:
            filter_query_str = " OR ".join(f"{DJANGO_CT}:{ct}" for ct in model_choices)
            # Insert a filter clause in OpenSearch DSL under "post_filter" to
            # filter by model
            model_filter = {"query_string": {"query": filter_query_str}}
            if "post_filter" in kwargs:
                # merge if another post filter exists
                prev_filter = kwargs["post_filter"]
                kwargs["post_filter"] = {"bool": {"must": [prev_filter, model_filter]}}
            else:
                kwargs["post_filter"] = model_filter

        return model_choices

    def _add_geo_filters_to_kwargs(
        self,
        filters: list[dict[str, Any]],
        within: dict[str, Any] | None,
        dwithin: dict[str, Any] | None,
    ) -> None:
        """
        Add geo filters to the filters list.

        Args:
            filters: The filters to add the geo filters to.
            within: The within filter to add to the filters.
            dwithin: The dwithin filter to add to the filters.

        """
        if within is not None:
            filters.append(self._build_search_query_within(within))
        if dwithin is not None:
            filters.append(self._build_search_query_dwithin(dwithin))

    def _apply_filters_to_query(
        self, kwargs: dict[str, Any], filters: list[dict[str, Any]]
    ) -> None:
        """
        Apply filters to the query, converting to bool query if needed.

        Args:
            kwargs: The search kwargs to apply the filters to.
            filters: The filters to apply to the search kwargs.

        """
        if not filters:
            return

        kwargs["query"] = {"bool": {"must": kwargs.pop("query")}}
        if len(filters) == 1:
            kwargs["query"]["bool"]["filter"] = filters[0]
        else:
            kwargs["query"]["bool"]["filter"] = {"bool": {"must": filters}}

    def build_search_kwargs(  # noqa: PLR0913
        self,
        query_string: str,
        sort_by: list[tuple[str, str]] | None = None,
        start_offset: int = 0,  # noqa: ARG002
        end_offset: int | None = None,  # noqa: ARG002
        fields: str | list[str] | set[str] = "",
        highlight: bool = False,
        facets: dict[str, Any] | None = None,
        date_facets: dict[str, Any] | None = None,
        query_facets: list[tuple[str, str]] | None = None,
        narrow_queries: set[str] | None = None,
        spelling_query: str | None = None,
        within: dict[str, Any] | None = None,
        dwithin: dict[str, Any] | None = None,
        distance_point: dict[str, Any] | None = None,
        models: Collection[Model] | None = None,
        limit_to_registered_models: bool | None = None,
        result_class: type[SearchResult] | None = None,  # noqa: ARG002
        **extra_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build search kwargs for OpenSearch query.

        Args:
            query_string: The query string to build the search kwargs for.

        Keyword Args:
            sort_by: The sort by configuration.
            start_offset: The start offset.
            end_offset: The end offset.
            fields: The fields to build the search kwargs for.
            highlight: The highlight configuration.
            facets: The facets to build the search kwargs for.
            date_facets: The date facets to build the search kwargs for.
            query_facets: The query facets to build the search kwargs for.
            narrow_queries: The narrow queries to build the search kwargs for.
            spelling_query: The spelling query to build the search kwargs for.
            within: The within filter to build the search kwargs for.
            dwithin: The dwithin filter to build the search kwargs for.
            distance_point: The distance point to build the search kwargs for.
            models: The models to build the search kwargs for.
            limit_to_registered_models: Whether to limit the models to
              registered models.
            result_class: The result class to build the search kwargs for.
            extra_kwargs: The extra kwargs to build the search kwargs for.

        Returns:
            A dictionary with the search kwargs.

        Raises:
            ImproperlyConfigured: If the connection alias is not configured.

        """
        index: UnifiedIndex = haystack.connections[
            self.connection_alias
        ].get_unified_index()
        content_field = index.document_field

        kwargs = self._build_query_string(query_string, content_field)
        filters: list[dict[str, dict[str, Any]]] = []

        self._add_fields_to_kwargs(kwargs, fields)
        self._add_sort_to_kwargs(kwargs, sort_by, distance_point)
        self._add_highlight_to_kwargs(kwargs, highlight, content_field)
        self._add_suggest_to_kwargs(
            kwargs, query_string, spelling_query, content_field, index
        )

        if narrow_queries is None:
            narrow_queries = set()

        self._add_facets_to_kwargs(kwargs, facets)
        self._add_date_facets_to_kwargs(kwargs, date_facets)
        self._add_query_facets_to_kwargs(kwargs, query_facets)

        model_choices = self._add_model_filters_to_kwargs(
            kwargs, models, limit_to_registered_models
        )
        if len(model_choices) > 0:
            filters.append({"terms": {DJANGO_CT: model_choices}})

        # Convert filter field queries into term filters
        term_filters = []
        for q in narrow_queries:
            # expected q is something like 'speaker_name_exact:"VALUE"'
            # parse out field and value
            field, value = q.split(":", 1)
            # strip quotes around the value if present
            value = value.strip('"')

            # Resolve the field name, stripping Haystack's '_exact' suffix if present
            if field.endswith("_exact"):
                field = self.get_facet_fieldname(field[:-6])

            term_filters.append({"term": {field: value}})
        filters.extend(term_filters)

        self._add_geo_filters_to_kwargs(filters, within, dwithin)
        self._apply_filters_to_query(kwargs, filters)

        if extra_kwargs:
            kwargs.update(extra_kwargs)

        return kwargs

    def _build_search_query_dwithin(self, dwithin: dict[str, Any]) -> dict[str, Any]:
        """
        Build geo_distance query for dwithin filter.

        Args:
            dwithin: The dwithin filter to build the query for.

        Returns:
            A dictionary with the geo_distance query.

        """
        lng, lat = dwithin["point"].coords
        distance = "{dist:.6f}{unit}".format(dist=dwithin["distance"].km, unit="km")
        return {
            "geo_distance": {
                "distance": distance,
                dwithin["field"]: {"lat": lat, "lon": lng},
            }
        }

    def _build_search_query_within(self, within: dict[str, Any]) -> dict[str, Any]:
        """
        Build geo_bounding_box query for within filter.

        Args:
            within: The within filter to build the query for.

        Returns:
            A dictionary with the geo_bounding_box query.

        """
        ((south, west), (north, east)) = generate_bounding_box(
            within["point_1"], within["point_2"]
        )
        return {
            "geo_bounding_box": {
                within["field"]: {
                    "top_left": {"lat": north, "lon": west},
                    "bottom_right": {"lat": south, "lon": east},
                }
            }
        }

    def _build_mlt_query(
        self, field_name, doc_id, additional_query_string, model_choices
    ):
        """Build more_like_this query."""
        mlt_query = {
            "query": {
                "more_like_this": {
                    "fields": [field_name],
                    "like": [
                        {
                            "_index": self.index_name,
                            "_id": doc_id,
                        },
                    ],
                }
            }
        }

        narrow_queries = []
        if additional_query_string and additional_query_string != "*:*":
            additional_filter = {"query_string": {"query": additional_query_string}}
            narrow_queries.append(additional_filter)

        if len(model_choices) > 0:
            model_filter = {"terms": {DJANGO_CT: model_choices}}
            narrow_queries.append(model_filter)

        if len(narrow_queries) > 0:
            mlt_query = {
                "query": {
                    "bool": {
                        "must": mlt_query["query"],
                        "filter": {"bool": {"must": list(narrow_queries)}},
                    }
                }
            }

        return mlt_query

    def more_like_this(  # noqa: PLR0913
        self,
        model_instance: Model,
        additional_query_string: str | None = None,
        start_offset: int = 0,
        end_offset: int | None = None,
        models: Collection[Model] | None = None,
        limit_to_registered_models: bool | None = None,
        result_class: type[SearchResult] | None = None,
        **kwargs,  # noqa: ARG002
    ):
        """
        Find documents similar to the given model instance.

        Args:
            model_instance: The model instance to find similar documents for.

        Keyword Args:
            additional_query_string: The additional query string to filter the
                documents.
            start_offset: The start offset.
            end_offset: The end offset.
            models: The models to find similar documents for.
            limit_to_registered_models: Whether to limit the models to
               registered models.
            result_class: The result class to use for the search results.
            kwargs: Additional keyword arguments to pass to the search.

        Returns:
            A list of search results.

        """
        if not self.setup_complete:
            self.setup()

        model_klass = model_instance._meta.concrete_model  # noqa: SLF001
        index = (
            connections[self.connection_alias]
            .get_unified_index()
            .get_index(model_klass)
        )
        field_name = index.get_content_field()
        params = {}

        if start_offset is not None:
            params["from_"] = start_offset

        if end_offset is not None:
            params["size"] = end_offset - start_offset

        doc_id = get_identifier(model_instance)

        if limit_to_registered_models is None:
            limit_to_registered_models = getattr(
                settings, "HAYSTACK_LIMIT_TO_REGISTERED_MODELS", True
            )

        if models and len(models):
            model_choices = sorted(get_model_ct(model) for model in models)
        elif limit_to_registered_models:
            model_choices = self.build_models_list()
        else:
            model_choices = []

        mlt_query = self._build_mlt_query(
            field_name, doc_id, additional_query_string, model_choices
        )

        try:
            raw_results = self.conn.search(
                body=mlt_query, index=self.index_name, _source=True, **params
            )
        except TransportError:
            if not self.silently_fail:
                raise

            self.log.exception(
                "Failed to fetch More Like This from OpenSearch for document '%s'",
                doc_id,
            )
            raw_results = {}

        return self._process_results(raw_results, result_class=result_class)

    def extract_file_contents(self, file_obj: Any) -> dict[str, Any] | None:
        """
        Extract text and metadata from a binary file using OpenSearch ingest-attachment.

        Args:
            file_obj: A file-like object containing the binary data.

        Returns:
            A dictionary with 'contents' and 'metadata', or None if extraction fails.

        """
        try:
            # Read and base64 encode the file content
            content = base64.b64encode(file_obj.read()).decode("utf-8")
        except Exception:
            if not self.silently_fail:
                raise
            self.log.exception("Failed to read and encode file for extraction")
            return None

        # Create a simulate pipeline body to extract the attachment
        body = {
            "pipeline": {
                "description": "Extract attachment information",
                "processors": [{"attachment": {"field": "data"}}],
            },
            "docs": [{"_source": {"data": content}}],
        }

        try:
            # Call OpenSearch ingest simulate API
            response = self.conn.ingest.simulate(body=body)

            if response and "docs" in response and len(response["docs"]) > 0:
                doc = response["docs"][0].get("doc", {})
                source = doc.get("_source", {})
                attachment = source.get("attachment", {})

                return {
                    "contents": attachment.get("content", ""),
                    "metadata": attachment.get("metadata", {}),
                }
        except Exception:
            if not self.silently_fail:
                raise
            self.log.exception("Failed to extract file contents from OpenSearch")

        return None

    def _build_search_params(self, kwargs, start_offset, end_offset):
        """Build search parameters including from/size."""
        if start_offset is not None:
            kwargs["from"] = start_offset

        if end_offset is not None and end_offset > start_offset:
            kwargs["size"] = end_offset - start_offset

        return kwargs

    def _execute_search(self, search_kwargs):
        """Execute the search query against OpenSearch."""
        try:
            raw_results = self.conn.search(
                body=search_kwargs,
                index=self.index_name,
                _source=True,
            )
        except TransportError:
            if not self.silently_fail:
                raise

            self.log.exception(
                "Failed to query OpenSearch using '%s'",
                search_kwargs.get("query", {}),
            )
            raw_results = {}

        return raw_results

    @log_query
    def search(self, query_string: str, **kwargs: Any) -> dict[str, Any]:
        """
        Search for documents matching the query string.

        Args:
            query_string: The query string to search for.
            kwargs: Additional keyword arguments to pass to the search.

        Returns:
            A dictionary with the search results.

        """
        if len(query_string) == 0:
            return {"results": [], "hits": 0}

        if not self.setup_complete:
            self.setup()

        search_kwargs = self.build_search_kwargs(query_string, **kwargs)
        start_offset = kwargs.get("start_offset", 0)
        end_offset = kwargs.get("end_offset")
        search_kwargs = self._build_search_params(
            search_kwargs, start_offset, end_offset
        )

        order_fields = set()
        for order in search_kwargs.get("sort", []):
            for key in order:
                order_fields.add(key)

        geo_sort = "_geo_distance" in order_fields

        raw_results = self._execute_search(search_kwargs)

        return self._process_results(
            raw_results,
            highlight=cast("bool | None", kwargs.get("highlight")),
            result_class=kwargs.get("result_class", SearchResult),
            distance_point=kwargs.get("distance_point"),
            geo_sort=geo_sort,
        )

    def _process_hits(self, raw_results: dict[str, Any]) -> int:
        """
        Extract hit count from raw results.

        Args:
            raw_results: The raw results to extract the hit count from.

        Returns:
            The hit count.

        """
        return raw_results.get("hits", {}).get("total", {}).get("value", 0)

    def _process_facets(self, raw_results: dict[str, Any]) -> dict[str, Any]:
        """
        Process facets/aggregations from raw results.

        Args:
            raw_results: The raw results to process the facets from.

        Returns:
            A dictionary with the processed facets.

        """
        facets: dict[str, Any] = {"fields": {}, "dates": {}, "queries": {}}
        if "aggregations" not in raw_results:
            return facets
        for facet_fieldname, facet_info in raw_results["aggregations"].items():
            facet_type = facet_info["meta"]["_type"]
            if facet_type == "terms":
                facets["fields"][facet_fieldname] = [
                    (individual["key"], individual["doc_count"])
                    for individual in facet_info["buckets"]
                ]
                if "order" in facet_info["meta"]:
                    if facet_info["meta"]["order"] == "reverse_count":
                        srt = sorted(
                            facets["fields"][facet_fieldname], key=lambda x: x[1]
                        )
                        facets["fields"][facet_fieldname] = srt
            elif facet_type == "date_histogram":
                facets["dates"][facet_fieldname] = [
                    (
                        datetime.datetime.fromtimestamp(
                            individual["key"] / 1000, datetime.UTC
                        ),
                        individual["doc_count"],
                    )
                    for individual in facet_info["buckets"]
                ]
            elif facet_type == "query":
                facets["queries"][facet_fieldname] = facet_info["doc_count"]

        return facets

    def _process_results(  # noqa: PLR0912
        self,
        raw_results: dict[str, Any],
        highlight: bool | None = None,  # noqa: ARG002
        result_class: type[SearchResult] | None = None,
        distance_point: dict[str, Any] | None = None,
        geo_sort: bool = False,
    ) -> dict[str, Any]:
        """
        Process raw search results into haystack SearchResult objects.

        Note:
            The ``highlight`` argument is accepted for API compatibility, but is
            not used.  OpenSearch returns highlight data in results if requested
            in the query, so this argument does not affect post-processing.

        Args:
            raw_results: The raw results to process.
            highlight: Whether to highlight the search results.
            result_class: The result class to use for the search results.
            distance_point: The distance point to use for the search results.
            geo_sort: Whether to sort the search results by geo distance.

        Returns:
            A dictionary with the processed results.

        """
        results = []
        hits = self._process_hits(raw_results)
        facets = {}
        spelling_suggestion = None

        if result_class is None:
            result_class = SearchResult

        if self.include_spelling and "suggest" in raw_results:
            raw_suggest = raw_results["suggest"].get("suggest")
            if raw_suggest:
                suggestion_parts = []
                for word in raw_suggest:
                    if len(word["options"]) > 0:
                        suggestion_parts.append(word["options"][0]["text"])
                    else:
                        suggestion_parts.append(word["text"])

                spelling_suggestion = " ".join(suggestion_parts)

        # Use our _process_facets method for OpenSearch 3.3 aggregations format
        facets = self._process_facets(raw_results)

        unified_index = haystack.connections[self.connection_alias].get_unified_index()
        indexed_models = unified_index.get_indexed_models()
        content_field = unified_index.document_field

        for raw_result in raw_results.get("hits", {}).get("hits", []):
            source = raw_result["_source"]
            app_label, model_name = source[DJANGO_CT].split(".")
            additional_fields = {}
            model = haystack_get_model(app_label, model_name)

            if model and model in indexed_models:
                index = source and unified_index.get_index(model)
                for key, value in source.items():
                    string_key = str(key)

                    if string_key in index.fields and hasattr(
                        index.fields[string_key], "convert"
                    ):
                        additional_fields[string_key] = index.fields[
                            string_key
                        ].convert(value)
                    else:
                        additional_fields[string_key] = self._to_python(value)

                del additional_fields[DJANGO_CT]
                del additional_fields[DJANGO_ID]

                if "highlight" in raw_result:
                    additional_fields["highlighted"] = raw_result["highlight"].get(
                        content_field, ""
                    )

                if distance_point:
                    additional_fields["_point_of_origin"] = distance_point

                    if geo_sort and raw_result.get("sort"):
                        additional_fields["_distance"] = Distance(
                            km=float(raw_result["sort"][0])
                        )
                    else:
                        additional_fields["_distance"] = None

                result = result_class(
                    app_label,
                    model_name,
                    source[DJANGO_ID],
                    raw_result["_score"],
                    **additional_fields,
                )
                results.append(result)
            else:
                hits -= 1

        return {
            "results": results,
            "hits": hits,
            "facets": facets,
            "spelling_suggestion": spelling_suggestion,
        }

    def _get_common_mapping(self) -> dict[str, Any]:
        """
        Get common mapping fields for all indices.

        Returns:
            A dictionary with the common mapping fields.

        """
        return {
            DJANGO_CT: {
                "type": "keyword",
            },
            DJANGO_ID: {
                "type": "keyword",
            },
        }

    def build_schema(self, fields: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """
        Build the schema/mapping for the index.

        Args:
            fields: The fields to build the schema for.

        Returns:
            A tuple with the content field name and the mapping.

        """
        content_field_name = ""
        mapping = self._get_common_mapping()

        for field_class in fields.values():
            field_mapping = self.FIELD_MAPPINGS.get(
                field_class.field_type, self.DEFAULT_FIELD_MAPPING
            ).copy()
            if field_class.boost != 1.0:
                field_mapping["boost"] = field_class.boost

            if field_class.document is True:
                content_field_name = field_class.index_fieldname
            if field_mapping["type"] == "text":
                if field_class.indexed is False or hasattr(field_class, "facet_for"):
                    field_mapping["type"] = "keyword"
                    del field_mapping["analyzer"]

            mapping[field_class.index_fieldname] = field_mapping

        return (content_field_name, mapping)


class OpenSearchSearchQuery(BaseSearchQuery):
    """OpenSearch search query class."""

    def matching_all_fragment(self) -> str:
        """
        Generate the query that matches all documents.

        Returns:
            The query that matches all documents.

        """
        return "*:*"

    def build_query_fragment(self, field: str, filter_type: str, value: Any) -> str:  # noqa: PLR0912, PLR0915
        """
        Generates a query fragment from a field, filter type and a value.

        Args:
            field: The field to build the query fragment for.
            filter_type: The filter type to build the query fragment for.
            value: The value to build the query fragment for.

        Returns:
            A query fragment.

        """
        query_frag: str = ""

        if not hasattr(value, "input_type_name"):
            # Handle when we've got a ``ValuesListQuerySet``...
            if hasattr(value, "values_list"):
                value = list(value)

            value = Clean(value) if isinstance(value, str) else PythonData(value)

        # Prepare the query using the InputType.
        prepared_value = value.prepare(self)

        if not isinstance(prepared_value, (set, list, tuple)):
            # Then convert whatever we get back to what OpenSearch wants if needed.
            prepared_value = self.backend._from_python(prepared_value)  # noqa: SLF001

        # 'content' is a special reserved word, much like 'pk' in
        # Django's ORM layer. It indicates 'no special field'.
        if field == "content":
            index_fieldname = ""
        else:
            index_fieldname = (
                haystack.connections[self._using]
                .get_unified_index()
                .get_index_fieldname(field)
            )

            # For exact matches, use the facet fieldname (which handles .keyword)
            if filter_type in ("exact", "in"):
                index_fieldname = self.backend.get_facet_fieldname(index_fieldname)

            index_fieldname = f"{index_fieldname}:"

        filter_types = {
            "content": "%s",
            "contains": "*%s*",
            "endswith": "*%s",
            "startswith": "%s*",
            "exact": "%s",
            "gt": "{%s TO *}",
            "gte": "[%s TO *]",
            "lt": "{* TO %s}",
            "lte": "[* TO %s]",
            "fuzzy": "%s~",
        }

        if value.post_process is False:
            query_frag = prepared_value
        else:  # noqa: PLR5501
            if filter_type in [
                "content",
                "contains",
                "startswith",
                "endswith",
                "fuzzy",
            ]:
                if value.input_type_name == "exact":
                    query_frag = prepared_value
                else:
                    # Iterate over terms & incorporate the converted form of
                    # each into the query.
                    terms: list[str] = []

                    if isinstance(prepared_value, str):
                        terms.extend(
                            filter_types[filter_type]
                            % self.backend._from_python(possible_value)  # noqa: SLF001
                            for possible_value in prepared_value.split(" ")
                        )
                    else:
                        terms.append(
                            filter_types[filter_type]
                            % self.backend._from_python(prepared_value)  # noqa: SLF001
                        )

                    if len(terms) == 1:
                        query_frag = terms[0]
                    else:
                        query_frag = "({})".format(" AND ".join(terms))
            elif filter_type == "in":
                in_options: list[str] = []

                if not prepared_value:
                    query_frag = "(!*:*)"
                else:
                    in_options.extend(
                        f'"{self.backend._from_python(possible_value)}"'  # noqa: SLF001
                        for possible_value in prepared_value
                    )
                    query_frag = "({})".format(" OR ".join(in_options))

            elif filter_type == "range":
                start = self.backend._from_python(prepared_value[0])  # noqa: SLF001
                end = self.backend._from_python(prepared_value[1])  # noqa: SLF001
                query_frag = f'["{start}" TO "{end}"]'
            elif filter_type == "exact":
                if value.input_type_name == "exact":
                    query_frag = prepared_value
                else:
                    prepared_value = Exact(prepared_value).prepare(self)
                    query_frag = filter_types[filter_type] % prepared_value
            else:
                if value.input_type_name != "exact":
                    prepared_value = Exact(prepared_value).prepare(self)

                query_frag = filter_types[filter_type] % prepared_value

        if len(query_frag) and not isinstance(value, Raw):
            if not query_frag.startswith("(") and not query_frag.endswith(")"):
                query_frag = f"({query_frag})"

        return f"{index_fieldname}{query_frag}"


class OpenSearchSearchEngine(BaseEngine):
    """OpenSearch search engine for django-haystack."""

    #: The backend for the search engine.
    backend: ClassVar[type[BaseSearchBackend]] = OpenSearchSearchBackend

    #: The query for the search engine.
    query: ClassVar[type[BaseSearchQuery]] = OpenSearchSearchQuery
