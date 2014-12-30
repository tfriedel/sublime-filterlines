import re

import sublime
import sublime_plugin


settings_path = 'Filter Lines.sublime-settings'


class PromptFoldToLinesCommand(sublime_plugin.WindowCommand):

    def run(self, search_type = 'string'):
        self.search_type = search_type

        settings = sublime.load_settings(settings_path)

        search_text = ""
        if settings.get('preserve_search', True):
            search_text = settings.get('latest_search', '')

        invert_search = settings.get('invert_search', False)

        if self.search_type == 'string':
            prompt = "Fold to lines %s: " % ('not containing' if invert_search else 'containing')
        else:
            prompt = "Fold to lines %s regex: " % ('not matching' if invert_search else 'matching')

        sublime.active_window().show_input_panel(prompt, search_text, self.on_done, None, None)


    def on_done(self, text):
        if self.window.active_view():
            settings = sublime.load_settings(settings_path)
            if settings.get('preserve_search', True):
                settings.set('latest_search', text)
            self.window.active_view().run_command("fold_to_lines", { "needle": text, "search_type": self.search_type })



class FoldToLinesCommand(sublime_plugin.TextCommand):

    def run(self, edit, needle, search_type):
        settings = sublime.load_settings('Filter Lines.sublime-settings')

        self.needle = needle
        self.search_type = search_type

        self.case_sensitive = False
        if search_type == 'string':
            self.case_sensitive = settings.get('case_sensitive_string_search', False)
        elif search_type == 'regex':
            self.case_sensitive = settings.get('case_sensitive_regex_search', True)

        self.invert_search = settings.get('invert_search', False)

        if search_type == 'string':
            self.match_pattern = re.compile(re.escape(self.needle), 0 if self.case_sensitive else re.IGNORECASE)
        else:
            self.match_pattern = re.compile(self.needle, 0 if self.case_sensitive else re.IGNORECASE)

        self.fold(edit)


    def fold(self, edit):
        regions = [ sublime.Region(0, self.view.size()) ]

        for region in reversed(regions):
            lines = self.view.split_by_newlines(region)
            folds = []

            for line in reversed(lines):
                matched = bool(self.match_pattern.search(self.view.substr(line))) ^ self.invert_search
                if matched and folds:
                    self.fold_regions(folds)
                    folds = []
                elif not matched:
                    folds.append(line)

            if folds:
                self.fold_regions(folds)


    def fold_regions(self, folds):
        region = sublime.Region(folds[0].end(), folds[0].end())
        for fold in folds:
            region = region.cover(fold)
        self.view.fold(region)
