from utils.db_utils import get_cursor_from_path, execute_sql_long_time_limitation
import json
import os, shutil
from tqdm.auto import tqdm
import argparse
def remove_contents_of_a_folder(index_path):
    # if index_path does not exist, then create it
    os.makedirs(index_path, exist_ok = True)
    # remove files in index_path
    for filename in os.listdir(index_path):
        file_path = os.path.join(index_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

def build_content_index(db_path, index_path):
    '''
    Create a BM25 index for all contents in a database
    '''
    cursor = get_cursor_from_path(db_path)
    results = execute_sql_long_time_limitation(cursor, "SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [result[0] for result in results]

    all_column_contents = []
    for table_name in tqdm(table_names):
        # skip SQLite system table: sqlite_sequence
        if table_name == "sqlite_sequence":
            continue
        results = execute_sql_long_time_limitation(cursor, "SELECT name FROM PRAGMA_TABLE_INFO('{}')".format(table_name))
        column_names_in_one_table = [result[0] for result in results]
        for column_name in tqdm(column_names_in_one_table):
            try:
                #print("SELECT DISTINCT `{}` FROM `{}` WHERE `{}` IS NOT NULL;".format(column_name, table_name, column_name))
                results = execute_sql_long_time_limitation(cursor, "SELECT DISTINCT `{}` FROM `{}` WHERE `{}` IS NOT NULL;".format(column_name, table_name, column_name))
                column_contents = [str(result[0]).strip() for result in results]

                for c_id, column_content in enumerate(column_contents):
                    # remove empty and extremely-long contents
                    if len(column_content) != 0 and len(column_content) <= 25:
                        all_column_contents.append(
                            {
                                "id": "{}-**-{}-**-{}".format(table_name, column_name, c_id).lower(),
                                "contents": column_content
                            }
                        )
            except Exception as e:
                print(str(e))

    os.makedirs('./data/temp_db_index', exist_ok = True)
    
    with open("./data/temp_db_index/contents.json", "w") as f:
        f.write(json.dumps(all_column_contents, indent = 2, ensure_ascii = True))

    # Building a BM25 Index (Direct Java Implementation), see https://github.com/castorini/pyserini/blob/master/docs/usage-index.md
    cmd = "python -m pyserini.index.lucene --collection JsonCollection --input ./data/temp_db_index --index {} --generator DefaultLuceneDocumentGenerator --threads 16 --storePositions --storeDocvectors --storeRaw".format(index_path)
    
    d = os.system(cmd)
    print(d)
    os.remove("./data/temp_db_index/contents.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db_root_path", type=str, help="path to the root databases")
    parser.add_argument("--index_path", type=str, help="result file path")
    print("build content index for BIRD's test set databases...")
    #remove_contents_of_a_folder("./data/sft_data_collections/bird/dev/dev_databases/")
    # build content index for BIRD's training set databases
    #    for db_id in os.listdir("./data/sft_data_collections/bird/dev/dev_databases/"):
    #       if db_id.endswith(".json"):
    #           continue
    #       print(db_id)
    #       build_content_index(
    #           os.path.join("./data/sft_data_collections/bird/dev/dev_databases/", db_id, db_id + ".sqlite"),
    #           os.path.join("./data/sft_data_collections/bird/dev/db_contents_index/", db_id)
    #       )


    args = parser.parse_args()
    for db_id in os.listdir(args.db_root_path):
       if db_id.endswith(".json"):
           continue
       print(db_id)
       build_content_index(
           os.path.join(args.db_root_path, db_id, db_id + ".sqlite"),
           os.path.join(args.index_path, db_id)
       )
