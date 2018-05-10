# Constellation
simple project & workflow manager for Sublime Text 3

Constellation grants one superpower--it can group existing projects into *a constellation* in order to open or close them as a group. Projects can be in more than one constellation.

![constellation](https://user-images.githubusercontent.com/2548365/39898663-5dc4dcae-547d-11e8-96ba-613f81c2078f.png)

	this alpha software
	needs polish and exercise
	lest it eat homework

## Getting started
1. Install Constellation via [Package Control](https://packagecontrol.io/)
2. Use the Constellation menu `[❉]` to `Create a constellation` and give it a short name.
3. Use the Constellation menu to `Open a constellation` and select the one you just added.
4. Use Sublime's `Project` menu to open one or more projects which you'd like to include.
5. Use the Constellation menu to `Add an open project`, select the constellation named in step 2, and select the (open) project you'd like to add. Repeat as necessary.

You can now close (and open) these projects by closing or opening the constellation.

## Rough edges
I hacked this together between builds to sand down a rough spot in my ST3 workflow. It meets these goals in my daily workflow and keeping it private seemed like a shame, but I don't have time to polish it for now. Could use help with these rough spots:

1. If multiple open constellations contain the same project, closing any will also close the project. #6

2. If you (or another plugin) are opening and closing projects, this plugin will still think a constellation is "open" after you manually close all of its projects. I recommend closing and reopening the constellation if you think it is out of step. #1

3. The "Add project by file" and "Upgrade & add workspace" commands:
	- won't work unless `find`, and `ln (link)` are available on your path (they lack detection, messaging and pure-python fallbacks)
	- are disabled by default on Windows for the same reason
	- are disabled on all platforms until you (manually, for now) add a "search_path" key to the root of your `Constellation.sublime-settings` file. This path tells Constellation where to run `find` (with `-maxdepth 5`) to search for project files.

## Contributing
I'll gladly triage feature requests, but the quickest way to get an approved feature incorporated will be a thoughtful pull request. If you'd like to help improve Constellation:

1. remove any local copy of Constellation (either through package control, or removing the directory if you cloned it)
2. fork this repo
3. `git clone` your fork into your ST3/Packages/ directory
4. create a new branch, improve Constellation, and submit a pull request
5. iterate if the Travis-CI build doesn't succeed

Changes should be accompanied by updates to relevant test cases and new ones when possible.
