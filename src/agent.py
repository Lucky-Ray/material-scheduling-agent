"""Stable CLI entry and public imports; implementation lives in separate modules."""
from cli import ROOT, main
from tools import Tools
from models import Model, MockModel
from runner import run

if __name__ == "__main__":
    main()
