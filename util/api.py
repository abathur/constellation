import sublime
import os
import time
from . import constants as c
from .subl import subl


class API:
    state = cache_dir = open_constellation_cache = None
    _open_constellations = set()

    @classmethod
    def load_state(cls, settings_file=None):
        print("load_state:0")
        cls.state = sublime.load_settings(settings_file or c.PLUGIN_SETTINGS_FILE) or {}
        print("load_state:1")

        constellations = cls.state.get("constellations", {})
        print("load_state:2")

        if not cls.cache_dir:
            print("load_state:3")
            cls.cache_dir = os.path.join(sublime.cache_path(), c.PLUGIN_NAME)
            cls.open_constellation_cache = os.path.join(
                cls.cache_dir, "open_constellations"
            )
            if not os.path.isdir(cls.cache_dir):
                print("load_state:4")
                os.mkdir(cls.cache_dir)

        try:
            print("load_state:5")
            with open(cls.open_constellation_cache) as cache:
                print("load_state:6")
                cls._open_constellations.update(
                    set(cache.read().splitlines()) & constellations.keys()
                )
        except FileNotFoundError:
            pass

        print("load_state:7")
        if not cls.state.get("did_migrate_open", False):
            print("load_state:8")
            cls.do_migrate_open(constellations)
        print("load_state:9")

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
        if name in self._open_constellations:
            return

        self._open_constellations.add(name)
        self.save_constellation_cache()
        print(
            "about to open constellation",
            name,
            self._open_constellations,
            [(win.id(), win.project_file_name()) for win in sublime.windows()],
        )
        projects_to_open = set(self.projects_for(name))
        for project in projects_to_open:
            subl("-n", project)
            # sometimes multiple projects don't open right; this superstitious pause seems to help.
            time.sleep(0.200)

        # DOING: lol
        time.sleep(2)
        """
        print(
            c.LOG_TEMPLATE,
            "Opened constellation:",
            name,
            self._open_constellations,
            [(win.id(), win.project_file_name()) for win in sublime.windows()],
        )

        waited = 0.0
        print("awaiting all projects to open", projects_to_open)
        while True:
            win_projects = set([win.project_file_name() for win in sublime.windows()])
            print("awaiting..., current window projects", win_projects)
            if win_projects.isdisjoint(projects_to_open):
                break
            else:
                time.sleep(0.200)
                waited += 0.2

        # time.sleep(2)
        # waited += 2.0
        print(
            c.LOG_TEMPLATE,
            waited,
            "seconds after opening:",
            name,
            self._open_constellations,
            [(win.id(), win.project_file_name()) for win in sublime.windows()],
        )
        # DOING: should this wait until it actually opens?
        """

    def close_constellation(self, name):
        print(
            "about to close constellation",
            name,
            self._open_constellations,
            [(win.id(), win.project_file_name()) for win in sublime.windows()],
        )
        self._open_constellations.remove(name)
        self.save_constellation_cache()
        print(c.LOG_TEMPLATE, "Closed constellation:", name)

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

    def projects_in_constellations(
        self,
    ):
        return {p for k, v in self.constellations.items() for p in v["projects"]}

    def add_to(self, name, project, already_open=False):
        if name and project:
            defined = self.constellations
            defined[name]["projects"].append(project)
            self.constellations = defined
            # print(c.LOG_TEMPLATE, "Add project:", project, "to", name)
            if not already_open and name in self._open_constellations:
                # open it, if the constellation is
                print(
                    "OPENING ADDED PROJECT",
                    project,
                    "WITH EXISTING WINDOWS",
                    [(win.id(), win.project_file_name()) for win in sublime.windows()],
                )
                subl("-n", project)
                time.sleep(2)

    def remove_from(self, name, project):
        if name and project:
            defined = self.constellations
            defined[name]["projects"].remove(project)
            self.constellations = defined
            # print(c.LOG_TEMPLATE, "Remove project:", project, "from", name)
