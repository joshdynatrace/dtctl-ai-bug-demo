from loguru import logger
from helpers import *

# TODO
# Sample Playwright app to headlessly spin up a browser and test the Dynatrace UI
# This type of test actually clicks the buttons and waits for data in the UI
# This is just a sample UI test showing some of what's possible
# You should, of course, complete this correctly for your app

TEST_TIMEOUT_SECONDS = os.environ.get("TESTING_TIMEOUT_SECONDS", 60)

@pytest.mark.timeout(TEST_TIMEOUT_SECONDS)
def test_dynatrace_ui(page: Page):

    app_name = "notebooks"

    ################################################
    logger.info("Logging in")
    login(page)

    # ################################################
    logger.info("Opening search menu")
    open_search_menu(page)
    
    # ################################################
    logger.info(f"Searching for {app_name}")
    app_name = "notebooks"
    search_for(page, app_name)

    # ################################################
    logger.info(f"Opening {app_name} app")
    open_app_from_search_modal(page, app_name)

    # ################################################
    logger.info(f"Creating a new document: ({app_name})")
    create_new_document(page=page, close_microguide=True)
    
    # ################################################
    # # Add a new section
    # # Remember to always increment the section_index
    # # for new sections
    # section_index = 0
    # search_term = "k6"
    # metric_text = "k6.vus"
    # logger.info(f"Adding a new {app_name} section. section_type={SECTION_TYPE_METRICS}. section_index={section_index}")
    # add_document_section(page=page, section_type_text=SECTION_TYPE_METRICS)
    # add_metric(page=page, search_term=search_term, metric_text=metric_text, section_index=section_index, validate=True)

    # ################################################
    section_index = 0
    section_type_text = "DQL"
    dql_query = retrieve_dql_query("fetch log line")
    
    logger.info(f"Adding a new {app_name} section. section_type={SECTION_TYPE_DQL}. section_index={section_index}")
    add_document_section(page=page, section_type_text=SECTION_TYPE_DQL)
    enter_dql_query(page=page, section_index=section_index, dql_query=dql_query, validate=True)

    # To prevent lots of dummy documents, delete the document created above 
    delete_document(page)
