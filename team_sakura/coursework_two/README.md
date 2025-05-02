# Team Sakura - Coursework 2
## Abstract

This project focuses on the design, development, and implementation of a functional data product for Corporate Social Responsibility (CSR) indicators, leveraging company CSR reports previously extracted and stored in a data lake.
The objective is to create a structured, reliable, and scalable solution that supports efficient storage, validation, and analysis of CSR data. 
The project involves identifying key sustainability thematic areas—such as deforestation, water consumption, and energy usage—and defining relevant indicators, metrics, and metadata. 
A robust infrastructure is developed using MongoDB to ensure scalable and dynamic data storage, accommodating varying indicator targets, revisions, and aims. 
To guarantee data quality and integrity, validation rules and metadata management practices are implemented. 
Additionally, the solution includes a visualization tool to enable intuitive data retrieval, analysis, and monitoring. 

## How to run the code?
1. Navigate to the read me file stored in team_sakura/coursework_one/a_pipeline/README.md file and refer to "How to run the code with Docker" to run main.py and extract CSR reports (don't forget to run )
#### Reminder from coursework one 
- Copy paste docker-compose.yml from team_sakura/coursework_one/a_pipeline/config/docker-compose.yml to root directory
- Run "docker compose up --build miniocw mongo_db minio_client_cw pipeline_runner" 
2. Once running the main.py script (Optional --> do CTRL C to not extract all CSR reports but still have a good database), exit coursework_one directory and navigate to team_sakura directory 
3. Enter your sensitive information (e.g. API Keys) by duplicating the .env.template stored in coursework_two/modules/config/.env.template and adding it to coursework_two directory
4. Run "poetry install"
5. Run "poetry run python coursework_two/main.py"
6. If wanting to reset the database, please run "RESET_DB=true poetry run python coursework_two/main.py" 

## How to view the indicators in mongo_db?
1. Navigate to mongo_db shell via Docker Terminal by running the command : "docker exec -it mongo_db_cw mongosh"
2. Run "use csr_reports_db2"
3. Run "db.sustainability_indicators.find().pretty()"

## How to view the indicators?
1. poetry run python app.py
2. Navigate to "http://127.0.0.1:5000/plot" to view plots
3. Navigate to "http://127.0.0.1:5000" to view and filter the indicators 

## How to run scheduling?
1. Navigate to team_sakura/coursework_two directory 
- Run  "poetry run python scheduler.py --frequency daily" for daily updates
- Run "poetry run python scheduler.py --frequency weekly" for weekly updates 
- Run "poetry run python scheduler.py --frequency monthly" for monthly updates

## How to run the tests?
- Run "poetry run pytest"

### Structure of Coursework Two:
```
├── team_sakura/
    ├──coursework_one/
    ├──coursework_two/
        └──docs/
        └──modules/
        	└──config/
        		└──.env.template
        		└──__init__.*
        		└──conf.yaml
        		└──env_loader.*
        	└──extractors/
        		└──__init__.*
        		└──deepseek_extractor.*
        		└──pdf_tools.*
        	└──report_availability/
        		└──CSR_availability.*
        	└──storage/
        		└──__init__.*
        		└──csv_writer.*
        		└──mongostore.*
        	└──test/
        	    └──CSR_availability_test.* 
        	    └──extract_year_test.*
        	    └──mongostore_test.*
        	    └──normalisation_test.*
        	    └──preprocessing_test.*
        	    └──standardization_test.*
        	└──utils
        		└──normalization.*
        		└──preprocessing.*
        		└──standardization.*
        		└──validation.*
        		└──year_extraction.*
        	└──visualization
        		└──static/
        		└──templates/
        			└──dashboard.html
        		└──utils/
        			└──db.*
        		└──app.*
        	└──__init__.*
        └──main.*
        └──README.md
        └──scheduler.*
        └──__init__.*
        

```
