from ..model.configuration import Configuration


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("graph", handler=handle_graph)
    cmd_parser.add_argument("component", nargs="?")
    cmd_parser.add_argument("--all-builds", action="store_true",
                            help="Include all builds instead of only the default one.")


def handle_graph(args, config: Configuration):
    if args.component:
        actions = [config.get_build(args.component).install]
    else:
        actions = set()
        for component in config.components.values():
            if args.all_builds:
                for build in component.builds.values():
                    actions.add(build.install)
            else:
                actions.add(component.default_build.install)

    print("digraph dependency_graph {")
    print("  splines=ortho")
    print_dependencies(actions)
    print("}")


def print_dependencies(actions):
    # TODO: this code needs to deduplicate rows and handle potential dependency cycles
    #  It is ugly and should be improved
    def _print_dependencies(action, already_visited_actions, rows):
        if action in already_visited_actions:
            return

        if action.is_satisfied(recursively=True):
            color = "green"
        elif action.can_run():
            color = "orange"
        else:
            color = "red"

        rows.add(f'  "{action.name_for_graph}"[ shape=box, style=filled, color={color} ];')
        for d in action.dependencies:
            rows.add(f'  "{d.name_for_graph}" -> "{action.name_for_graph}";')

        already_visited_actions.add(action)

        for d in action.dependencies:
            _print_dependencies(d, already_visited_actions, rows)

    already_visited_actions = set()
    rows = set()
    for action in actions:
        _print_dependencies(action, already_visited_actions, rows)
    for r in sorted(rows):
        print(r)
