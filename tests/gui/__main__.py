
import sys
from . import context_by_name, graphic_items


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
        Tuple[String, String, Controller, String]: first element is the name
            of the context selected. The second item is the name of the module
            selected. The third item is the controller. The last item is the
            name of the view class present in the module.
    """

    if len(args) == 0 or len(args) > 2:
        display_usage()
        sys.exit(1)

    try:
        controller, view_module, view_list = graphic_items[args[0]]
    except KeyError:
        display_usage(error='"%s" does not exists.' % args[0])
        sys.exit(1)

    try:
        context_name = args[1]
    except IndexError:
        if len(view_list) == 1:
            context_name = next(iter(view_list.keys()))
        else:
            display_usage(select_context=list(view_list))
            sys.exit(1)

    try:
        view_name = view_list[context_name]
    except KeyError:
        display_usage(
            error="Implementation '%s' not available for '%s'" %
                  (args[1], args[0]),
            select_context=view_list)
        sys.exit(1)
    return context_name, view_module, view_name, controller


def main(*args):
    ctx_name, view_module, view_name, controller = get_target_element(*args)

    context = context_by_name[ctx_name]
    gen = context()
    exit_func = next(gen)  # Initialize context
    import importlib

    # Note: import must be done after context initialization.
    print('bajoo.gui.%s.%s_%s_view'
          % (view_module, '.'.split(view_module)[-1], 'wx'))
    view_module = importlib.import_module(
        'bajoo.gui.%s.%s_%s_view' % (view_module,
                                     view_module.split('.')[-1], ctx_name))

    view = getattr(view_module, view_name)
    controller(view, exit_func)

    try:
        next(gen)  # execute loop start here
    except StopIteration:
        pass


if __name__ == '__main__':
    args = sys.argv[1:]
    main(*args)
