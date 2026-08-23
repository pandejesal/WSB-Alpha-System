import logging

logger = logging.getLogger(__name__)

def main():
    """
    NOTE: The Streamlit dashboard is deprecated.
    The real dashboard is now a static HTML site located in `docs/` and hosted via GitHub Pages.
    Data for the new dashboard is populated by CI actions and stored in `docs/data/`.
    """
    logger.info("This Streamlit dashboard is deprecated. Please refer to the docs/ HTML dashboard instead.")
    print("Dashboard is deprecated. Please use the static GitHub Pages dashboard in docs/.")

if __name__ == '__main__':
    main()
