import sys
from cli.commands import execute

def main():
    # If no args are provided (other than the script name), 
    # we want to default to `chat` or just let execute() handle it.
    # execute() defaults to chat if args.command is None.
    execute(sys.argv[1:])

if __name__ == "__main__":
    main()
