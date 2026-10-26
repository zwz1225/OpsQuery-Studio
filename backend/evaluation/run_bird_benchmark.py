"""Separate external entry point; never routes BIRD cases to operational runners."""
from evaluation.bird.runner import main

if __name__=='__main__':main()
