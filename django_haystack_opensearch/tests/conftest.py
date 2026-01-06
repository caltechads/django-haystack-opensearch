class MockField:
    def __init__(self, field_type, faceted=False):
        self.field_type = field_type
        self.faceted = faceted


class MockIndex:
    def __init__(self, fields):
        self.fields = fields


class MockUnifiedIndex:
    def __init__(self, model_fields_map):
        self.model_fields_map = model_fields_map

    def get_indexed_models(self):
        return list(self.model_fields_map.keys())

    def get_index(self, model):
        return MockIndex(self.model_fields_map[model])
