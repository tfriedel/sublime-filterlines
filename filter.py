import functools
import itertools
import re

import sublime
import sublime_plugin


class PromptFilterToLinesCommand(sublime_plugin.WindowCommand):

    def run(self, search_type = 'string'):
        self.search_type = search_type

        settings = sublime.load_settings('Filter Lines.sublime-settings')

        search_text = ""
        if settings.get('preserve_search', True):
            search_text = settings.get('latest_search', '')

        invert_search = settings.get('invert_search', False)

        if self.search_type == 'string':
            prompt = "Filter to lines %s: " % ('not containing' if invert_search else 'containing')
        else:
            prompt = "Filter to lines %s regex: " % ('not matching' if invert_search else 'matching')

        sublime.active_window().show_input_panel(prompt, search_text, self.on_done, None, None)


    def on_done(self, text):
        if self.window.active_view():
            settings = sublime.load_settings('Filter Lines.sublime-settings')
            if settings.get('preserve_search', True):
                settings.set('latest_search', text)

            if (settings.get('custom_separator', False) and
                    settings.get('use_new_buffer_for_filter_results', True)):
                f = functools.partial(self.on_separator, text)
                default_sep = settings.get('default_custom_separator', r'(\n|\r\n|\r)')
                sublime.active_window().show_input_panel('Custom regex separator', default_sep, f, None, None)
                return

            self.window.active_view().run_command("filter_to_lines", { "needle": text, "search_type": self.search_type })


    def on_separator(self, text, separator):
        self.window.active_view().run_command("filter_to_lines", {
            "needle": text, "search_type": self.search_type,
            "separator": separator})



class FilterToLinesCommand(sublime_plugin.TextCommand):

    def run(self, edit, needle, search_type, separator=None):
        sublime.status_message("Filtering")

        self.needle = needle
        self.search_type = search_type
        self.separator = separator

        settings = sublime.load_settings('Filter Lines.sublime-settings')

        if search_type == 'string':
            self.case_sensitive = settings.get('case_sensitive_string_search', False)
        elif search_type == 'regex':
            self.case_sensitive = settings.get('case_sensitive_regex_search', True)

        self.invert_search = settings.get('invert_search', False)

        if self.search_type == 'string':
            self.match_pattern = re.compile(re.escape(self.needle), 0 if self.case_sensitive else re.IGNORECASE)
        else:
            self.match_pattern = re.compile(self.needle, 0 if self.case_sensitive else re.IGNORECASE)

        if settings.get('use_new_buffer_for_filter_results', True):
            self.filter_to_new_buffer(edit)
        else:
            self.filter_in_place(edit)

        sublime.status_message("")


    def filter_to_new_buffer(self, edit):
        results_view = self.view.window().new_file()
        results_view.set_name('Filter Results')
        results_view.set_scratch(True)
        results_view.settings().set('word_wrap', self.view.settings().get('word_wrap'))

        regions = [ sublime.Region(0, self.view.size()) ]

        if self.separator is None:
            lines = (self.view.split_by_newlines(r) for r in regions)
            lines = map(self.view.substr, itertools.chain.from_iterable(lines))
        else:
            lines = itertools.chain.from_iterable(self.itersplit(separator, self.view.substr(r)) for r in regions)

        text = ''
        for line in lines:
            if bool(self.match_pattern.search(line)) ^ self.invert_search:
                if self.separator is None:
                    line += '\n'
                text += line

        results_view.run_command(
            'append', {'characters': text, 'force': True,
                       'scroll_to_end': False})

        if results_view.size() > 0:
            results_view.set_syntax_file(self.view.settings().get('syntax'))
        else:
            message = 'Filtering for "%s" %s\n\n0 matches\n' % (self.needle, '(case-sensitive)' if self.case_sensitive else '(not case-sensitive)')
            results_view.run_command('append', { 'characters': message, 'force': True, 'scroll_to_end': False })


    def filter_in_place(self, edit):
        regions = [ sublime.Region(0, self.view.size()) ]

        for region in reversed(regions):
            lines = self.view.split_by_newlines(region)
            for line in reversed(lines):
                if not (bool(self.match_pattern.search(line)) ^ self.invert_search):
                    self.view.erase(edit, self.view.full_line(line))    


    def itersplit(self, sep, s):
        exp = re.compile(sep)
        pos = 0
        old_start = 0
        from_begin = False
        while True:
            m = exp.search(s, pos)
            if not m:
                if pos < len(s):
                    if not from_begin:
                        yield s[pos:]
                    else:
                        yield s[old_start:]
                break
            if pos < m.start() and not from_begin:
                yield s[pos:m.end()]
            elif from_begin:
                yield s[old_start:m.start()]
            elif m.start() == 0:
                # pattern is found at beginning, reverse yielding slices
                from_begin = True
            pos = m.end()
            old_start = m.start()
