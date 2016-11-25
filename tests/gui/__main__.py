
import sys
from . import graphic_items


def display_usage(error=None, select_context=None):
    print("""Usage: python -m tests.gui graphic_element [context]

Show a GUI element for testing purposes.

arguments:
  graphic_element \tName of graphic element to show.
  context         \tIf the selected element has several implementations, name
                  \tof the implementation. 'wx' and 'gtk' are common values.
""")
    if error:
        print('%s\n' % error)

    if select_context:
        print('The selected element has several implementations:\n')
        for name in select_context:
            print('  %s' % name)
    else:
        print("List of elements available:\n")
        for name in graphic_items:
            print('  %s' % name)


def get_target_element(*args):
    """Get the context, controller and view to use, from arguments.

    Returns:
        Tuple[Callable, Controller, String]: first element is a generator
            function used to initialize and stop the graphic context. The
            second item is the controller. The last item is the name of the
            view class present in `bajoo.gui.views`.
    """

    if len(args) == 0 or len(args) > 2:
        display_usage()
        sys.exit(1)

    try:
        controller, view_list = graphic_items[args[0]]
    except KeyError:
        display_usage(error='"%s" does not exists.' % args[0])
        sys.exit(1)

    try:
        context_name = args[1]
    except IndexError:
        if len(view_list) == 1:
            context_name = view_list.keys()[0]
        else:
            display_usage(select_context=list(view_list))
            sys.exit(1)

    try:
        context, view_name = view_list[context_name]
    except KeyError:
        display_usage(
            error="Implementation '%s' not available for '%s'" %
                  (args[1], args[0]),
            select_context=view_list)
        sys.exit(1)
    return context, view_name, controller


def main(*args):
    context, view_name, controller = get_target_element(*args)

    gen = context()
    exit_func = next(gen)  # Initialize context

    # Note: import must be done after context initialization.
    from bajoo.gui import views

    view = getattr(views, view_name)
    controller(view, exit_func)

    try:
        next(gen)  # execute loop start here
    except StopIteration:
        pass


if __name__ == '__main__':
    args = sys.argv[1:]
    main(*args)
