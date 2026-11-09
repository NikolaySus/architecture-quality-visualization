"""Run from the repository root: python -m research.language_resources --help."""

import argparse
import json
import sys

from filelock import Timeout

from . import pipeline
from .storage import CATALOG, Workspace
from .warehouse import rebuild


def main(argv=None):
    parser = argparse.ArgumentParser(description="Локальные языковые ресурсы и исследовательский граф")
    parser.add_argument("--home", help="Рабочий каталог; также LANGUAGE_RESOURCES_HOME")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["download", "sync"]:
        command = commands.add_parser(name)
        command.add_argument("--source", nargs="+", choices=list(CATALOG))
        if name == "sync":
            command.add_argument("--force", action="store_true")
    importer = commands.add_parser("import")
    importer.add_argument("source", choices=list(CATALOG))
    importer.add_argument("path")
    importer.add_argument("--complete", action="store_true", help="Полнота ручной выгрузки проверена пользователем")
    builder = commands.add_parser("rebuild")
    builder.add_argument("--force", action="store_true")
    commands.add_parser("status")
    component_parser = commands.add_parser("components", help="Компоненты слабой связности и доли источников в крупнейшей")
    component_parser.add_argument("--details", action="store_true", help="Состав, связи и происхождение остальных компонент")
    args = parser.parse_args(argv)
    workspace = Workspace(args.home)
    try:
        if args.command == "download":
            result = pipeline.download(workspace, args.source)
            failed = any(item["status"] != "ok" for item in result.values())
        elif args.command == "sync":
            result = pipeline.sync(workspace, args.source, args.force)
            failed = any(item["status"] != "ok" for item in result["downloads"].values())
        elif args.command == "import":
            result = pipeline.import_local(workspace, args.source, args.path, args.complete)
            failed = not result["complete"]
        elif args.command == "rebuild":
            result = rebuild(workspace, args.force)
            failed = False
        elif args.command == "components":
            from .connectivity import components
            result = components(workspace, details=args.details)
            failed = False
        else:
            result = pipeline.status(workspace)
            failed = False
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if failed else 0
    except Timeout:
        print("Другой процесс обновляет рабочий каталог. Повторите запуск после его завершения.", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
