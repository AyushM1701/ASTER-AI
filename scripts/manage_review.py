"""Local manual blinded-review export/import; no external transfer.

Reviewer declarations are externally unverified. Protect the private registry
and assignment token files using the host's user permissions. Never place them
in shared datasets, public release bundles or routine logs.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.data.review import ReviewStore  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--cases", type=Path, required=True)
    create.add_argument("--rubric", type=Path, required=True)
    create.add_argument("--source-version", required=True)
    create.add_argument("--seed", type=int, default=0)
    create.add_argument("--local-review-authorized", action="store_true", required=True)
    register = commands.add_parser("register")
    register.add_argument("--reviewer", type=Path, required=True, help="Private identity/qualification declaration JSON")
    assign = commands.add_parser("assign")
    assign.add_argument("--batch", required=True)
    assign.add_argument("--reviewer-id", required=True)
    assign.add_argument("--role", choices=["reviewer", "adjudicator"], default="reviewer")
    assign.add_argument("--token-file", type=Path, required=True)
    for name in ("export", "import"):
        command = commands.add_parser(name)
        command.add_argument("--token-file", type=Path, required=True)
        command.add_argument("--output" if name == "export" else "--submission", type=Path, required=True)
    report = commands.add_parser("report")
    report.add_argument("--batch", required=True)
    args = parser.parse_args()
    store = ReviewStore(args.registry)
    try:
        if args.command == "create":
            result = {"batch_id": store.create_batch(read(args.cases), read(args.rubric), seed=args.seed,
                                                     source_version=args.source_version, rights="local_review_authorized"),
                      "qualified_review": "pending"}
        elif args.command == "register":
            declaration = read(args.reviewer)
            identity = declaration.pop("identity")
            store.register_reviewer(identity, **declaration)
            result = {"registration": "private_declaration_saved; credentials_externally_unverified"}
        elif args.command == "assign":
            if args.token_file.exists():
                raise FileExistsError("Token file exists; never overwrite an assignment")
            assignment, _ = store.assign(args.batch, args.reviewer_id, args.role,
                                         deliver=lambda identity, token: write_new(args.token_file, {"assignment_id": identity, "token": token}))
            result = {"assignment_id": assignment, "token_written": True}
        elif args.command in {"export", "import"}:
            authorization = read(args.token_file)
            if args.command == "export":
                write_new(args.output, store.packet(authorization["assignment_id"], authorization["token"]))
                result = {"exported_locally": True, "qualified_review": "pending"}
            else:
                result = store.import_reviews(authorization["assignment_id"], authorization["token"], read(args.submission))
        else:
            result = store.report(args.batch)
        print(json.dumps(result, indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    main()
