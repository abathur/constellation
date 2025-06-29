"""
Collect ST3 projects/workspaces into "Constellations"

When you open or close a constellation, it opens or closes all of the included projects.
"""

import sublime
import sublime_plugin

import os
import subprocess
import time
import json

from .util import input_handlers as collect
from .util.api import API
from .util import constants as c


def plugin_loaded():
    # print("plugin_loaded:pre-load_state")
    API.load_state()
    # print("plugin_loaded:post-load_state")


def plugin_unloaded():
    API.save_state()


class _BaseApplicationCommand(sublime_plugin.ApplicationCommand, API):
    pass


# TODO: I won't pretend to completely grok when and why ST3's api uses the various arg-passing conventions it's using. May be worth a refactor when this is better understood.


class OpenConstellationsInfoCommand(_BaseApplicationCommand):
    def is_enabled(self, *args):
        return False

    def description(self, *args):
        return "Open Constellations: {:}/{:}".format(
            len(self._open_constellations), len(self.active_constellations())
        )


# TODO: can remove below when a pure python or Windows-safe fallback for 'find' is implemented
class WindowsUserQuestionCommand(_BaseApplicationCommand):
    def is_enabled(self, *args):
        return False

    def description(self, *args):
        return "Help wanted (see github) on these:"


class OpenConstellationsCommand(_BaseApplicationCommand):
    def is_visible(self, index=None, **args):
        return index < len(self._open_constellations)

    def is_enabled(self, index=None, **args):
        return True

    def description(self, index=None, **args):
        const = relevant = None
        if index < len(self._open_constellations):
            relevant = self.open_constellations()
            const = relevant[index]
        return (
            "    {} [{}]".format(
                const, "∗" * len(self.constellations[const]["projects"])
            )
            if index < len(relevant)
            else "Oops. You shouldn't be seeing this. Better find someone who works here."
        )

    def run(self, index=None, **args):
        if index < len(self._open_constellations):
            relevant = self.open_constellations()
            const = relevant[index]
            return CloseConstellationCommand().run(const)


class _ExistingConstellationCommand(_BaseApplicationCommand):
    _list_class = collect.SelectConstellationList

    def input(self, constellation):
        return self._list_class()

    def is_enabled(self, constellation=None, **kwargs):
        return True if len(self._list_class._generator(self)) else False


class _OpenConstellationCommand(_ExistingConstellationCommand):
    _list_class = collect.SelectOpenConstellationList


class _ClosedConstellationCommand(_ExistingConstellationCommand):
    _list_class = collect.SelectClosedConstellationList


class _ActiveConstellationCommand(_ExistingConstellationCommand):
    _list_class = collect.SelectActiveConstellationList


class ManageConstellationsInfoCommand(_BaseApplicationCommand):
    def is_enabled(self, *args):
        return False

    def description(self, *args):
        return "Constellations"


class CreateConstellationCommand(_BaseApplicationCommand):
    def input(self, args):
        return collect.InputConstellationName()

    def run(self, name):
        self.add_constellation(name)
        self.open_constellation(name)


class CreateConstellationFromOpenProjectCommand(_BaseApplicationCommand):
    def input(self, args):
        return collect.OpenProjectList(exclude=self.projects_in_constellations())

    def run(self, project):
        name = os.path.splitext(os.path.basename(project))[0]
        self.add_constellation(name)
        self.open_constellation(name)
        # add project to eponymous constellation
        self.add_to(name, project, already_open=True)


class CreateConstellationFromProjectFileCommand(_BaseApplicationCommand):
    def input(self, args):
        return collect.SearchProjectList()

    def run(self, project):
        name = os.path.splitext(os.path.basename(project))[0]
        self.add_constellation(name)
        self.open_constellation(name)
        # add project to eponymous constellation
        self.add_to(name, project)


class CreateConstellationFromWorkspaceFileCommand(_BaseApplicationCommand):
    def input(self, args):
        return collect.UpgradeWorkspaceList()

    def run(self, project):
        name = os.path.splitext(os.path.basename(project))[0]
        self.add_constellation(name)
        self.open_constellation(name)
        # add project to eponymous constellation
        self.add_to(name, project)


class DestroyConstellationCommand(_ActiveConstellationCommand):
    def run(self, constellation):
        if constellation not in self.constellations:
            return

        if constellation in self._open_constellations:
            self.close_constellation(constellation)

        self.remove_constellation(constellation)


class RenameConstellationCommand(_ActiveConstellationCommand):
    def input(self, args):
        return collect.RenameList()

    def run(self, constellation, new_name):
        if constellation not in self.constellations:
            return
        self.rename_constellation(constellation, new_name)


class OpenConstellationCommand(_ClosedConstellationCommand):
    def run(self, constellation):
        self.open_constellation(constellation)


class CloseConstellationCommand(_OpenConstellationCommand):
    def run(self, constellation):
        print(
            "CloseConstellation.run.1",
            self._open_constellations,
            [(win.id(), win.project_file_name()) for win in sublime.windows()],
            sublime.active_window().id(),
        )
        if constellation not in self._open_constellations:
            return

        any_pending = True
        while any_pending:
            print("1:start", any_pending)
            any_pending = False
            for project in self.projects_for(constellation):
                print("2:start", any_pending, project)
                for window in sublime.windows():
                    print(
                        "3:start consider closing workspace",
                        project,
                        window.project_file_name(),
                        "this window=",
                        window.id(),
                        "active window=",
                        sublime.active_window().id(),
                        window.is_valid(),
                    )
                    if window.project_file_name() == project:
                        print("3.1: CLOSING WORKSPACE")
                        time.sleep(0.2)
                        # window.run_command("close_workspace")
                        window.run_command("close_project")
                        any_pending = True
                        # waited = 0.0
                        # while window.project_file_name() == project and waited <= 30.0:
                        #     # any_pending = True
                        #     print(
                        #         "Time spent trying to get the workspace to close",
                        #         waited,
                        #     )
                        #     time.sleep(0.2)
                        #     waited += 0.2
                        #     # window.run_command("close_workspace")
                        #     window.run_command(
                        #         "close_project"
                        #     )  # DOING: wait, THIS works?

                        if len(sublime.windows()) == 1:
                            print("3.1: OPENING EMPTY WINDOW")

                            window.run_command("new_window")
                            time.sleep(0.2)

                        print("3.1: CLOSING WINDOW")
                        window.run_command("close_window")
                        time.sleep(0.2)

                        """
                        TODO: document why you're carving this out?
                        (guess: to avoid closing last window, esp. on non-macOS)
                        let's try only respecting this heuristic when there's 1 window?

                        DOING:
                        under the assumption that this is indeed why I'm doing it
                        I wonder if it's ~cleaner to just open a new window?

                        if len(sublime.windows()) == 1:
                            window.run_command("new_window")

                        if (
                            window.id() != sublime.active_window().id()
                            and len(sublime.windows()) != 1
                        ):
                            window.run_command("close_window")
                        else:
                            window.run_command("close_window")
                        """
                    print("3:end", any_pending, window.id(), window.project_file_name())
                print("2:end", any_pending, project)
            print("1:end", any_pending)

        """
        DOING:
        something racy/flaky causing tests to fail
        condition appears to be constellation marked closed but projects in it still open, at which point the verification closure for close_constellation can't resolve true anymore

        I guess the ~right thing to do here is to ensure we only try to close it once all projects cleanly close?

        (I guess this could hang if there's a reason it can't close...)

        Thoughts on the right way to implement
            - set up an event listener to handle on_window_command and on_post_window_command, hold state on each of these commands as they start, drop state as they finish, and let this function either hang to await that completion, or queue a setTimeout that will check this and either close the constellation once done or requeue?
            - hang this function to actively check open projects/windows at close time until all are gone
                let's do the dumbest thing first

        I guess one more thesis here is that close_window closes the active window regardless of which window object you run it on, in which case the race or nondeterminism might be around which window counts as active? maybe go compare the active IDs across working/failing flows?
            not saying I think this is true
        """
        print(
            "CloseConstellation.run.2",
            self._open_constellations,
            [(win.id(), win.project_file_name()) for win in sublime.windows()],
            sublime.active_window().id(),
        )
        self.close_constellation(constellation)
        print(
            "CloseConstellation.run.3",
            self._open_constellations,
            [(win.id(), win.project_file_name()) for win in sublime.windows()],
            sublime.active_window().id(),
        )


class ManageProjectsInfoCommand(_BaseApplicationCommand):
    def is_enabled(self, *args):
        return False

    def description(self, *args):
        return "Constellation Projects"


def commonprefix(l):
    # something borrowed: https://stackoverflow.com/questions/21498939/how-to-circumvent-the-fallacy-of-pythons-os-path-commonprefix
    # this unlike the os.path.commonprefix version
    # always returns path prefixes as it compares
    # path component wise
    if getattr(os.path, "commonpath", None):
        return os.path.commonpath(l)
    cp = []
    ls = [p.split("/") for p in l]
    ml = min(len(p) for p in ls)

    for i in range(ml):

        s = set(p[i] for p in ls)
        if len(s) != 1:
            break

        cp.append(s.pop())

    return "/".join(cp)


class AddProjectCommand(_ActiveConstellationCommand):
    already_open = True

    # def guess_search_path(self):
    #     """
    #     Use common root of open projects to guess
    #     where user stores theirs.

    #     Uses lowercase comparison since caseless filesystems
    #     may have a mix of upper/lower paths loaded in ST
    #     without the user noticing, causing it to back out
    #     further than necessary.

    #     When there aren't open projects it'll fall back to the root which can be quite slow.

    #     Caution:
    #     I'm skeptical this is the "right" approach, but
    #     it's a testing expediency for now. It would probably
    #     be better to just add a command for setting the
    #     project search root and disable all other commands
    #     until one is set?
    #     """
    #     project_files = [
    #         y.lower() for y in [x.project_file_name() for x in sublime.windows()] if y
    #     ]
    #     return commonprefix(project_files) if project_files else os.path.expanduser("~")

    def input(self, args):
        return collect.ProjectList()

    def run(self, constellation, project):
        print(self.__class__.__name__, "run", constellation, project)
        self.add_to(constellation, project, already_open=self.already_open)


# We have opinions, and one of those is that workspaces are annoying to work with directly. Because of this opinion, the only way we're going to support working with them is by explicitly upgrading it to a project (but then replacing the project file with a link back to whatever project the workspace was in) so you get the benefits of having a workspace, but we don't have to have arcane methods of working with them.


class UpgradeWorkspaceCommand(AddProjectCommand):
    already_open = False

    def is_enabled(self, *args):
        # TODO: remove below when there's a fallback
        if sublime.platform() == "windows":
            return False
        search_root = self.search_path if self.search_path else os.path.expanduser("~")
        return (
            True
            if search_root and len(search_root) and os.path.exists(search_root)
            else False
        )

    def input(self, args):
        return collect.FoundWorkspaceList()

    def run(self, constellation, workspace_path):
        if not workspace_path:
            # print(c.LOG_TEMPLATE, "Nothing found to upgrade")
            return

        workspace = None

        # load the workspace
        with open(workspace_path, "r") as infile:
            workspace = json.load(infile)

        project = os.path.join(os.path.dirname(workspace_path), workspace["project"])
        workspace_project = workspace_path.replace(
            ".sublime-workspace", ".sublime-project"
        )

        if len(workspace["project"]) and os.path.exists(project):
            # this seems to be set to a real value, so we'll make a link to the sublime-project
            subprocess.Popen(
                "ln -f '{:}' '{:}'".format(project, workspace_project), shell=True
            )
        elif not os.path.exists(workspace_project):
            # some projects might have a null value, or maybe the file got deleted, so we'll just make an empty project
            with open(workspace_project, "w") as outfile:
                json.dump({}, outfile, indent=1)
        else:
            pass
            # print(
            #     c.LOG_TEMPLATE,
            #     "I really hope we never get here",
            #     workspace,
            #     workspace_project,
            #     workspace_path,
            #     project,
            # )

        workspace["project"] = workspace_project

        with open(workspace_path, "w") as outfile:
            json.dump(workspace, outfile, indent=1)

        super().run(constellation, workspace_project)

        # at this point, we need to have taken the workspace file, added a link adjacent to the project file, and replaced the project key in the workspace file with the pointer to the adjacent file


class FindProjectCommand(AddProjectCommand):
    already_open = False

    def is_enabled(self, *args):
        # TODO: remove below when there's a fallback
        if sublime.platform() == "windows":
            return False

        search_root = self.search_path if self.search_path else os.path.expanduser("~")

        # print(
        #     self.__class__.__name__,
        #     "is_enabled",
        #     args,
        #     "search_path",
        #     search_root,
        #     len(search_root),
        #     os.path.exists(search_root),
        # )
        return (
            True
            if search_root and len(search_root) and os.path.exists(search_root)
            else False
        )

    def input(self, args):
        print(self.__class__.__name__, "input", args)
        return collect.FoundProjectList()


class RemoveProjectCommand(_ActiveConstellationCommand):
    def input(self, args):
        return collect.ConstellationProjectList()

    def run(self, constellation, project):
        self.remove_from(constellation, project)
