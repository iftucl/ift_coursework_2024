# To run the my_fastapi and data_storage test:

cd coursework_two
poetry run pytest test/my_fastapi/ test/data_storage/ --cov=modules --cov=my_fastapi --cov-report=html
start htmlcov/index.html
