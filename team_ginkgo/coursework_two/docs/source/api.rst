API Reference
============

This section provides detailed documentation for all modules, classes, and functions in the project.

.. toctree::
   :maxdepth: 2

   api/modules
   api/classes
   api/functions

The documentation is organized into three main sections:

1. Module Documentation
   - Main application module
   - Database module
   - Output module

2. Class Documentation
   - BaseModel
   - DataService

3. Function Documentation
   - Process data functions
   - Validation functions

Module Documentation
------------------

.. automodule:: main
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: __weakref__

   .. autofunction:: menu
   .. autofunction:: main

Database Module
--------------

.. automodule:: db
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: __weakref__

   .. autofunction:: create_reports_with_indicators

Output Module
------------

.. automodule:: output
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: __weakref__

   .. autofunction:: main

Class Documentation
-----------------

.. autoclass:: src.models.BaseModel
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: __weakref__

.. autoclass:: src.services.DataService
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: __weakref__

Function Documentation
--------------------

.. autofunction:: src.utils.helpers.process_data
   :noindex:

.. autofunction:: src.utils.helpers.validate_input
   :noindex: 