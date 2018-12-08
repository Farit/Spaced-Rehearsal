class Formatting:
    """
    Why we need \001 and \002 escapes, answer provided from the
    https://bugs.python.org/issue20359:

    Thanks again for the responses and your help. After a bit of research,
    I discovered the /reasons/ behind needing the \001 and \002 escapes.
    Thought I'd log the links here for posterity sake:
      - To color something in on a color capable terminal console you just
        need to use the "\033[<color code>m" escape sequence.
        This would be sufficient[1]
      - However readline messes up the line width calculation because it
        measures the escape sequences as a characters too. To avoid this you
        have to wrap the escape sequences within \001 and \002.[2]
      - On some terminal applications (like the one I am using - terminator[3]),
        if you add the \001 and \002 escapes to color text which is *not*
        interpreted by readline, (for instance if you have a single function
        to color text and you want to use it to color both your sys.ps1 and
        output text), the \001 and \002 codes will get printed out using a
        representation (like a unicode 'box'[4]). So, one would have to
        workaround that in the text coloring function.

        [1] http://en.wikipedia.org/wiki/ANSI_escape_code#Colors
        [2] bugs.python.org/issue17337/ and
            http://stackoverflow.com/questions/9468435/look-how-to-fix-column-calculation-in-python-readline-if-use-color-prompt
        [3] http://gnometerminator.blogspot.sg/p/introduction.html
        [4] http://en.wikipedia.org/wiki/Control_character#Display

    Examples:
        TermColor.red('hello')
        TermColor.red('hello', is_escape_seq=True)

    """
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    LIGHT_BLUE = '\033[1;34m'
    PURPLE = '\033[35m'
    GREY = '\033[1;30m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    def red(self, text, is_escape_seq=False):
        return self._wrap(text, colour=self.RED, is_escape_seq=is_escape_seq)

    def green(self, text, is_escape_seq=False):
        return self._wrap(text, colour=self.GREEN, is_escape_seq=is_escape_seq)
        
    def yellow(self, text, is_escape_seq=False):
        return self._wrap(
                text, colour=self.YELLOW, is_escape_seq=is_escape_seq
        )

    def blue(self, text, is_escape_seq=False):
        return self._wrap(
                text, colour=self.BLUE, is_escape_seq=is_escape_seq
        )

    def light_blue(self, text, is_escape_seq=False):
        return self._wrap(
                text, colour=self.LIGHT_BLUE, is_escape_seq=is_escape_seq
        )

    def purple(self, text, is_escape_seq=False):
        return self._wrap(
                text, colour=self.PURPLE, is_escape_seq=is_escape_seq
        )

    def grey(self, text, is_escape_seq=False):
        return self._wrap(
                text, colour=self.GREY, is_escape_seq=is_escape_seq
        )

    def bold(self, text, is_escape_seq=False):
        return self._wrap(
                text, colour=self.BOLD, is_escape_seq=is_escape_seq
        )

    def underline(self, text, is_escape_seq=False):
        return self._wrap(
                text, colour=self.UNDERLINE, is_escape_seq=is_escape_seq
        )

    def _wrap(self, text, *, colour, is_escape_seq=False):
        end = self.END
        if is_escape_seq:
            colour = f'\x01{colour}\x02'
            end = f'\x01{end}\x02'
        return colour + str(text) + end
