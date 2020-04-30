import sublime
import os
from . import constants as c


class API:
    state = cache_dir = open_constellation_cache = None
    _open_constellations = set()

    @classmethod
    def load_state(cls, settings_file=None):
        cls.state = sublime.load_settings(settings_file or c.PLUGIN_SETTINGS_FILE) or {}

        constellations = cls.state.get("constellations", {})

        if not cls.cache_dir:
            cls.cache_dir = os.path.join(sublime.cache_path(), c.PLUGIN_NAME)
            cls.open_constellation_cache = os.path.join(
                cls.cache_dir, "open_constellations"
            )
            if not os.path.isdir(cls.cache_dir):
                os.mkdir(cls.cache_dir)
                os.path.mknod(cls.open_constellation_cache)

        try:
            with open(cls.open_constellation_cache) as cache:
                cls._open_constellations.update(
                    set(cache.read().splitlines()) & constellations.keys()
                )
        except FileNotFoundError:
            pass

        if not cls.state.get("did_migrate_open", False):
            cls.do_migrate_open(constellations)

    @classmethod
    def do_migrate_open(cls, constellations):
        for name, settings in constellations.items():
            if "open" in settings:
                if settings["open"]:
                    cls._open_constellations.add(name)
                del settings["open"]

        cls.state.set("constellations", constellations)
        cls.state.set("did_migrate_open", True)

    @classmethod
    def save_state(cls, settings_file=None):
        sublime.save_settings(settings_file or c.PLUGIN_SETTINGS_FILE)
        with open(cls.open_constellation_cache, mode="w") as cache:
            cache.write(
                "\n".join(
                    cls._open_constellations
                    & cls.state.get("constellations", {}).keys()
                )
            )

    @property
    def constellations(self):
        return self.state.get("constellations", {})

    @constellations.setter
    def constellations(self, value):
        self.state.set("constellations", value)
        self.save_state()

    def open_constellations(self):
        """Open"""
        return list(self._open_constellations)

    @property
    def open_projects(self):
        """Open"""
        return list(
            set(
                [
                    win.project_file_name()
                    for win in sublime.windows()
                    if win.project_file_name()
                ]
            )
        )

    def closed_constellations(self):
        """Active, but not open"""
        return self.active_constellations() - self._open_constellations

    def archived_constellations(self):
        return {
            k
            for k, v in self.state.get("constellations", {}).items()
            if v.get("archived")
        }

    def active_constellations(self):
        return {
            k
            for k, v in self.state.get("constellations", {}).items()
            if not v.get("archived")
        }

    @property
    def search_path(self):
        return self.state.get("search_path", "")

    @search_path.setter
    def search_path(self, value):
        self.state.set("search_path", value)
        self.save_state()

    def add_constellation(self, name):
        defined = self.constellations
        defined[name] = {"archived": False, "projects": []}
        self.constellations = defined
        # print(c.LOG_TEMPLATE, "Created constellation:", name)

    def remove_constellation(self, name):
        defined = self.constellations
        del defined[name]
        self.constellations = defined
        # print(c.LOG_TEMPLATE, "Removed constellation:", name)

    @classmethod
    def save_constellation_cache(cls):
        with open(cls.open_constellation_cache, mode="w") as cache:
            for line in (
                cls._open_constellations & cls.state.get("constellations", {}).keys()
            ):
                cache.write(line + "\n")

    def open_constellation(self, name):
        self._open_constellations.add(name)
        self.save_constellation_cache()
        # print(c.LOG_TEMPLATE, "Opened constellation:", name)

    def close_constellation(self, name):
        self._open_constellations.remove(name)
        self.save_constellation_cache()
        # print(c.LOG_TEMPLATE, "Closed constellation:", name)

    def archive_constellation(self, name):
        defined = self.constellations
        defined[name]["archived"] = True
        self.constellations = defined

    def unarchive_constellation(self, name):
        defined = self.constellations
        defined[name]["archived"] = False
        self.constellations = defined

    def rename_constellation(self, name, new_name):
        defined = self.constellations
        defined[new_name] = defined[name]
        del defined[name]
        self.constellations = defined
        # print(c.LOG_TEMPLATE, "Renamed constellation:", name, "->", new_name)

    def projects_for(self, name):
        return self.constellations[name]["projects"]

    def add_to(self, name, project):
        if name and project:
            defined = self.constellations
            defined[name]["projects"].append(project)
            self.constellations = defined
            # print(c.LOG_TEMPLATE, "Add project:", project, "to", name)

    def remove_from(self, name, project):
        if name and project:
            defined = self.constellations
            defined[name]["projects"].remove(project)
            self.constellations = defined
            # print(c.LOG_TEMPLATE, "Remove project:", project, "from", name)
