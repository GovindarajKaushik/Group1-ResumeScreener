# Root CLI entry point delegating to the OOP Main controller

from OOP.main import CLIController, Main

if __name__ == "__main__":
    app: CLIController = Main()
    app.run()
