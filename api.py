import sublime
from . import constants as c


class API:
    state = None

    @classmethod
    def load_state(cls, settings_file=None):
        cls.state = sublime.load_settings(settings_file or c.PLUGIN_SETTINGS_FILE) or {}

    @classmethod
    def save_state(cls, settings_file=None):
        sublime.save_settings(settings_file or c.PLUGIN_SETTINGS_FILE)

    @property
    def constellations(self):
        return self.state.get("constellations", {})

    @constellations.setter
    def constellations(self, value):
        self.state.set("constellations", value)
        self.save_state()

    @property
    def open_constellations(self):
        """Open"""
        return [
            k for k, v in self.state.get("constellations", {}).items() if v.get("open")
        ]

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

    @property
    def closed_constellations(self):
        """Active, but not open"""
        return [
            k
            for k, v in self.state.get("constellations", {}).items()
            if not v.get("archived") and not v.get("open")
        ]

    @property
    def archived_constellations(self):
        return [
            k
            for k, v in self.state.get("constellations", {}).items()
            if v.get("archived")
        ]

    @property
    def active_constellations(self):
        return [
            k
            for k, v in self.state.get("constellations", {}).items()
            if not v.get("archived")
        ]

    @property
    def search_path(self):
        return self.state.get("search_path", "")

    @search_path.setter
    def search_path(self, value):
        self.state.set("search_path", value)
        self.save_state()

    def add_constellation(self, name):
        defined = self.constellations
        defined[name] = {"archived": False, "open": False, "projects": []}
        self.constellations = defined
        # print(c.LOG_TEMPLATE, "Created constellation:", name)

    def remove_constellation(self, name):
        defined = self.constellations
        del defined[name]
        self.constellations = defined
        # print(c.LOG_TEMPLATE, "Removed constellation:", name)

    def open_constellation(self, name):
        defined = self.constellations
        defined[name]["open"] = True
        self.constellations = defined
        # print(c.LOG_TEMPLATE, "Opened constellation:", name)

    def close_constellation(self, name):
        defined = self.constellations
        defined[name]["open"] = False
        self.constellations = defined
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
