
class TermColor:
    PURPLE = '\033[35m'
    BLUE = '\033[34m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @classmethod
    def coloralize(cls, color, string_to_color):
        return color + string_to_color + cls.END

    @classmethod
    def red(cls, string_to_color):
        return cls.coloralize(cls.RED, string_to_color)

    @classmethod
    def yellow(cls, string_to_color):
        return cls.coloralize(cls.YELLOW, string_to_color)

    @classmethod
    def green(cls, string_to_color):
        return cls.coloralize(cls.GREEN, string_to_color)

    @classmethod
    def bold(cls, string_to_color):
        return cls.coloralize(cls.BOLD, string_to_color)

    @classmethod
    def underline(cls, string_to_color):
        return cls.coloralize(cls.UNDERLINE, string_to_color)

