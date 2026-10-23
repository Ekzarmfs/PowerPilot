"""
PowerPilot — Battery Optimization & Process Management for Windows 11
Entry point for the application.
"""

import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Launch the PowerPilot application."""
    from app import PowerPilotApp


    app = PowerPilotApp()
    app.run()


if __name__ == "__main__":
    main()
