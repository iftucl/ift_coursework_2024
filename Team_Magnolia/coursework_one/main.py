# Main entry point for Team Magnolia's CSR pipeline system
# Provides a unified command-line interface to all components
#
# AVAILABLE COMMANDS:
# ------------------
# scrape:  Run the CSR scraper to collect PDF reports from company websites.
#          The scraper will extract data from each company's website,
#          download PDF reports, store them in MinIO, and save metadata to MongoDB.
#
# fix:     Run the data cleanup utility to enhance report metadata.
#          This fixes report years by extracting them from PDF content,
#          standardizes data formats, and removes duplicate reports.
#
# index:   Create or update MongoDB indexes for faster API queries.
#          Sets up indexes for company name, report year, and text search
#          which dramatically improves query performance.
#
# api:     Launch the FastAPI server for CSR data retrieval.
#          Provides REST API endpoints to search and download reports.
#
import argparse
import logging
import sys
import os

# ======================================
# 1. Attempt imports from your modules
# ======================================

run_scraper = None

try:
    # Import the analysis pipeline for sentiment analysis and text extraction
    from modules.api.analysis_pipeline import run_analysis
except ImportError:
    run_analysis = None

try:
    # Import the data cleanup utility for fixing report metadata
    from modules.scraper.csr_fix_and_cleanup import main as run_fix_and_cleanup
except ImportError:
    run_fix_and_cleanup = None

try:
    # Import the MongoDB index setup utility
    from modules.api.mongo_index_setup import setup_indexes
except ImportError:
    setup_indexes = None

try:
    # Import the FastAPI app for serving report data
    from modules.api.fastapi_api import app as fastapi_app
except ImportError:
    fastapi_app = None

# Import Uvicorn for running the FastAPI server
import uvicorn

# ======================================
# 2. Logging Configuration
# ======================================
# Set up standardized logging for all components
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ======================================
# 3. Argument Parsing
# ======================================
def parse_args():
    # Create the main argument parser with description
    parser = argparse.ArgumentParser(
        description="Main entry point for the CSR data pipeline."
    )
    # Require a subcommand to be specified
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 3.1 Subcommand: scrape
    # This command runs the web scraper to collect CSR PDFs
    scrape_parser = subparsers.add_parser(
        "scrape",
        help="Run the CSR scraper pipeline (fetch new PDF reports, store in MinIO & MongoDB)."
    )
    # Optional limit to number of companies processed
    scrape_parser.add_argument(
        "--max-companies",
        type=int,
        default=None,
        help="Limit the number of companies to scrape (optional)."
    )

    scrape_parser.add_argument(
        "--local-selenium",
        action="store_true",
        help="Enable local Chrome/Chromedriver fallback even when no SELENIUM_URL is set."
    )

    # Comment out analysis parser
    '''
    # 3.2 Subcommand: analysis
    analysis_parser = subparsers.add_parser(
        "analysis",
        help="Run data analysis tasks, e.g., text extraction or sentiment analysis."
    )
    analysis_parser.add_argument(
        "--quick",
        action="store_true",
        help="Use a quick mode, skip heavier tasks."
    )
    '''

    # 3.3 Subcommand: fix
    # This command runs the data cleanup and repair utilities
    fix_parser = subparsers.add_parser(
        "fix",
        help="Run the fix/cleanup script for correcting years, removing duplicates, etc."
    )
    # Option to simulate changes without actually making them
    fix_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making database changes."
    )

    # 3.4 Subcommand: index
    # This command creates/updates MongoDB indexes
    index_parser = subparsers.add_parser(
        "index",
        help="Create or update MongoDB indexes."
    )

    # 3.5 Subcommand: api
    # This command starts the FastAPI server
    api_parser = subparsers.add_parser(
        "api",
        help="Launch the FastAPI server for CSR data retrieval."
    )
    # Host to bind the API server to
    api_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the API (default: 0.0.0.0)."
    )
    # Port to run the API server on
    api_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the API (default: 8000)."
    )
    # Option for development mode with auto-reloading
    api_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable Uvicorn auto-reload (dev mode)."
    )

    return parser.parse_args()

# ======================================
# 4. Main Logic
# ======================================
def main():
    # Parse command-line arguments
    args = parse_args()

    # Route to appropriate function based on subcommand
    if args.command == "scrape":
        # Run the web scraper to collect CSR reports
        logger.info("Starting the CSR scraper pipeline...")

        # Set env flag for local selenium before importing the scraper
        if args.local_selenium:
            os.environ["ALLOW_LOCAL_SELENIUM"] = "true"

        # Lazy import of scraper AFTER env variable is set so constants evaluate correctly
        try:
            from importlib import import_module, reload
            scraper_module = import_module("modules.scraper.csr_scraper")
            # Reload to ensure module-level constants pick up new env vars
            scraper_module = reload(scraper_module)
            scraper_module.main(max_companies=args.max_companies)
        except ImportError as e:
            logger.error(f"Failed to import scraper module: {e}")
        logger.info("Finished the CSR scraping process!")

    
    elif args.command == "analysis":
        # Run text extraction and sentiment analysis on PDFs
        logger.info("Starting analysis pipeline...")
        if run_analysis:
            run_analysis(quick_mode=args.quick)
        else:
            logger.error("Analysis pipeline not found or not imported.")
        logger.info("Finished the analysis pipeline!")

    elif args.command == "fix":
        # Run data cleanup and repair utilities
        logger.info("Running fix/cleanup script...")
        if run_fix_and_cleanup:
            # Pass dry_run flag to simulate changes without making them
            run_fix_and_cleanup(dry_run=args.dry_run)
        else:
            logger.error("Fix/cleanup script not found or not imported.")
        logger.info("Cleanup tasks completed!")

    elif args.command == "index":
        # Create or update MongoDB indexes for query optimization
        logger.info("Creating/Updating MongoDB indexes...")
        if setup_indexes:
            setup_indexes()
        else:
            logger.error("Mongo index setup not found or not imported.")
        logger.info("Mongo indexes updated successfully!")

    elif args.command == "api":
        # Start the FastAPI server for data access
        logger.info("Launching FastAPI server...")
        if fastapi_app:
            # Run uvicorn with the specified host, port, and reload options
            uvicorn.run(
                "modules.api.fastapi_api:app",
                host=args.host,
                port=args.port,
                reload=args.reload
            )
        else:
            logger.error("FastAPI app not found or not imported.")
        logger.info("FastAPI server stopped.")

# ======================================
# 5. Entry Point
# ======================================
if __name__ == "__main__":
    # Run the main function when script is executed directly
    main()
