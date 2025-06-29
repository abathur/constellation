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
        cls.state = sublime.load_settings(settings_file or c.PLUGIN_SETTINGS_FILE) or {}

        constellations = cls.state.get("constellations", {})

        if not cls.cache_dir:
            cls.cache_dir = os.path.join(sublime.cache_path(), c.PLUGIN_NAME)
            cls.open_constellation_cache = os.path.join(
                cls.cache_dir, "open_constellations"
            )
            if not os.path.isdir(cls.cache_dir):
                os.mkdir(cls.cache_dir)

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
        if name in self._open_constellations:
            return

        self._open_constellations.add(name)
        self.save_constellation_cache()

        use_internal_command = int(sublime.version()) >= 4000

        # print(c.LOG_TEMPLATE, "Opened constellation:", name)
        for project in set(self.projects_for(name)):
            if use_internal_command:
                print("using open_project_or_workspace to open", project)
                sublime.active_window().run_command(
                    "open_project_or_workspace",
                    {"file": project, "new_window": True},
                )
            else:
                subl("-n", project)
                # sometimes multiple projects don't open right; this superstitious pause seems to help.
                time.sleep(0.200)

        """
        CAUTION:
        While trying to debug projects not showing up as open,
        I've wondered if this should just sleep until all projects
        are open before returning.

        Something about this doesn't work. My best guess is that,
        because we shell out to `subl` to open the project, we are
        trying to wait for something that won't run until we return.
        """

    def close_constellation(self, name):
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

    def add_to(self, name, project, should_already_be_open=False):
        if name and project:
            # TODO: undo this assignment dance to see if there's
            # a good reason for it
            defined = self.constellations
            if project in defined[name]["projects"]:
                return  # already added it

            defined[name]["projects"].append(project)
            self.constellations = defined
            print(c.LOG_TEMPLATE, "Add project:", project, "to", name)
            if not should_already_be_open and name in self._open_constellations:
                """
                already_open is about the type of command, and the
                UI helps us keep users from misusing it. API users
                (like our own tests) can misuse this, so we'll check
                """
                if project not in [
                    win.project_file_name() for win in sublime.windows()
                ]:
                    if int(sublime.version()) >= 4000:
                        print("using open_project_or_workspace to open", project)
                        sublime.active_window().run_command(
                            "open_project_or_workspace",
                            {"file": project, "new_window": True},
                        )
                    else:
                        time.sleep(2)
                        # open it, if the constellation is
                        print("actually invoking subl to open", project)
                        subl("-n", project)
                        # superstitious pause (confirmed in CI: Oct 4 2026)
                        time.sleep(2)

    def remove_from(self, name, project):
        if name and project:
            defined = self.constellations
            defined[name]["projects"].remove(project)
            self.constellations = defined
            # print(c.LOG_TEMPLATE, "Remove project:", project, "from", name)
