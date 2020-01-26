from functools import partial


class Formatting:
    # \u001b - ESCAPE unicode character
    RED = '\u001b[31m'
    GREEN = '\u001b[32m'
    YELLOW = '\u001b[33m'
    BLUE = '\u001b[34m'
    WHITE = '\u001b[37m'
    LIGHT_BLUE = '\u001b[1;34m'
    PURPLE = '\u001b[35m'
    GREY = '\u001b[90m'
    END = '\u001b[0m'
    BOLD = '\u001b[1m'
    UNDERLINE = '\u001b[4m'

    def __getattr__(self, color_name):
        """
        >>> formatting = Formatting()
        >>> msg = formatting.red('hello')
        """
        if not hasattr(self, color_name.upper()):
            raise AttributeError(color_name)
        return partial(self._wrap, colour=getattr(self, color_name.upper()))

    def _wrap(self, text, *, colour, is_escape_color_codes=False):
        end = self.END
        if is_escape_color_codes:
            # For the interactive prompt we need correctly calculate the line width.
            # We should not count the color escape sequences as characters.
            #
            # 'readline' messes up the line width calculation because it
            # measures the escape sequences as a characters too. To avoid this you
            # have to wrap the escape sequences within \001 and \002.
            colour = f'\x01{colour}\x02'
            end = f'\x01{end}\x02'
        return colour + str(text) + end
