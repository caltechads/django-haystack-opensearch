from django.contrib import admin
from django.template.defaultfilters import linebreaksbr
from unfold.admin import ModelAdmin

from .models import Act, Play, Scene, Speaker, Speech


@admin.register(Speech)
class SpeechAdmin(ModelAdmin):
    list_display = (
        "id",
        "speaker",
        "text_as_verse",
        "scene__act__play",
        "act_bare",
        "scene_bare",
        "created_date",
    )
    list_filter = ("speaker", "scene", "scene__act", "scene__act__play", "created_date")
    search_fields = (
        "text",
        "speaker__name",
        "scene__name",
        "scene__act__name",
        "scene__act__play__title",
    )
    ordering = ("scene__act__play", "scene__act", "scene", "order")
    list_per_page = 100
    list_max_show_all = 100
    list_display_links = ("id", "text_as_verse")
    list_select_related = ("speaker", "scene", "scene__act", "scene__act__play")

    @admin.display(description="Text", ordering="text")
    def text_as_verse(self, obj: Speech) -> str:
        return linebreaksbr(obj.text)

    @admin.display(description="Scene", ordering="scene")
    def scene_bare(self, obj: Scene) -> str:
        return obj.scene.name

    @admin.display(description="Act", ordering="scene")
    def act_bare(self, obj: Act) -> str:
        return obj.scene.act.name


@admin.register(Play)
class PlayAdmin(ModelAdmin):
    list_display = ("id", "title", "created")
    list_filter = ("created",)
    search_fields = ("title",)
    ordering = ("-created",)
    list_per_page = 100
    list_max_show_all = 100
    list_display_links = ("id", "title")


@admin.register(Speaker)
class SpeakerAdmin(ModelAdmin):
    list_display = ("id", "name", "speeches_count", "scenes_count", "plays_count")
    list_filter = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 100
    list_max_show_all = 100
    list_display_links = ("id", "name")

    @admin.display(description="# Speeches", ordering="speeches")
    def speeches_count(self, obj: Speaker) -> int:
        return obj.speeches.count()

    @admin.display(description="# Scenes", ordering="scenes")
    def scenes_count(self, obj: Speaker) -> int:
        n_scenes = 0
        scenes_seen = set()
        for scene in obj.speeches.all().values_list("scene", flat=True):
            if scene not in scenes_seen:
                scenes_seen.add(scene)
                n_scenes += 1
        return n_scenes

    @admin.display(description="# Plays", ordering="plays")
    def plays_count(self, obj: Speaker) -> int:
        n_plays = 0
        plays_seen = set()
        for scene in obj.speeches.all().values_list("scene", flat=True):
            _scene = Scene.objects.get(pk=scene)
            if _scene.act.play not in plays_seen:
                plays_seen.add(_scene.act.play)
                n_plays += 1
        return n_plays


@admin.register(Act)
class ActAdmin(ModelAdmin):
    list_display = ("id", "name", "play", "order")
    list_filter = ("play", "order")
    search_fields = ("name", "play__title")
    ordering = ("play", "order")
    list_per_page = 100
    list_max_show_all = 100
    list_display_links = ("id", "name")
    list_select_related = ("play",)


@admin.register(Scene)
class SceneAdmin(ModelAdmin):
    list_display = ("id", "play__title", "act_bare", "scene_bare", "order")
    list_filter = ("play", "act")
    search_fields = ("name", "act__name", "play__title", "id")
    ordering = ("play", "act", "order")
    list_per_page = 100
    list_max_show_all = 100
    list_display_links = ("id", "name")
    list_select_related = ("act",)

    @admin.display(description="Scene", ordering="scene")
    def scene_bare(self, obj: Scene) -> str:
        return obj.name

    @admin.display(description="Act", ordering="scene")
    def act_bare(self, obj: Act) -> str:
        return obj.act.name
