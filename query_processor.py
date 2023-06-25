import csv
import mysql_handler
import postgres_handler
import os

schema = None

commands = {}


def write_csv(table: str, cursor, colum_names: list, schema: str) -> bool:
    path_for_file = catch_table_path(table, schema)
    table_data = []
    tables_data = {}  # Dicionário de tabelas(listas) = Nosso banco de dados

    for row in cursor:
        table_data.append(row)

    tables_data[table] = table_data
    # headers = cursor.column_names

    with open(path_for_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=colum_names)
        writer.writeheader()
        writer.writerows(table_data)


# returns a list of a dict with keys as column name of a csv file
def read_csv(table_path: str) -> list:
    with open(table_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        data = []
        for row in reader:
            data.append(row)
        return data


def data_from_table(table, schema) -> list:
    if check_existing_table(table, schema):
        table_path = catch_table_path(table, schema)
        data = read_csv(table_path=table_path)
        return data


def tuple_value(data: tuple) -> str:
    if data != None:
        return data[0]
    else:
        return None


def _join(data1: list, data2: list):
    result = []

    if tuple_value(commands["on"]) != None:
        try:
            on_value = tuple_value(commands["on"])
            # remove ()
            on_value = on_value.strip("(")
            on_value = on_value.strip(")")

            on_value = on_value.split("=")

            command_for_table_1 = on_value[0].split(".")
            command_for_table_2 = on_value[1].split(".")

            name_table_1 = command_for_table_1[0]
            column_table_1 = command_for_table_1[1]

            name_table_2 = command_for_table_2[0]
            column_table_2 = command_for_table_2[1]

            if (
                tuple_value(commands["from"]) == name_table_1
                and tuple_value(commands["join"]) == name_table_2
            ):
                for item1 in data1:
                    for item2 in data2:
                        if item1[column_table_1] == item2[column_table_2]:
                            result.append({**item1, **item2})
                return result
            elif (
                tuple_value(commands["from"]) == name_table_2
                and tuple_value(commands["join"]) == name_table_1
            ):
                for item1 in data1:
                    for item2 in data2:
                        if item1[column_table_2] == item2[column_table_1]:
                            result.append({**item1, **item2})
                return result
            else:
                print("Error : Wrong arguments near {}".format(on_value))
                return False

        except:
            print("Error : Wrong argument near {}".format(on_value))
            return False

    elif tuple_value(commands["using"]) != None:
        try:
            using_value = tuple_value(commands["using"])
            using_value = using_value.strip(")")
            using_value = using_value.strip("(")
            column = using_value

            for item1 in data1:
                for item2 in data2:
                    if item1[column] == item2[column]:
                        # item2.pop(column) #removes equal column
                        result.append({**item1, **item2})
            return result

        except:
            print("Error : Wrong argument near {}".format(using_value))
            return False

    else:
        print("Error : Wrong argument near join")
        return False


def _from():
    global schema
    global commands

    data = []

    try:
        table_from = tuple_value(commands["from"])
        data_from = data_from_table(table_from, schema)
        data = data_from

        if tuple_value(commands["join"]) != None:
            table_join = tuple_value(commands["join"])
            data_join = data_from_table(table_join, schema)
            data = _join(data_from, data_join)

        return data

    except:
        print("Error : Wrong arguments near {}".format(table_from))
        return False


def _where(data):
    try:
        if tuple_value(commands["where"]) == None:
            return data
        else:
            if tuple_value(commands["and"]) != None:
                word_cond1 = tuple_value(commands["where"])
                word_cond2 = tuple_value(
                    commands["and"]
                )  # catch value passed after AND statement
                filtered_data = [
                    row
                    for row in data
                    if condition_func(word_cond1, row)
                    and condition_func(word_cond2, row)
                ]  # here using list comprehensions
            elif tuple_value(commands["or"]) != None:
                word_cond1 = tuple_value(commands["where"])
                word_cond2 = tuple_value(
                    commands["or"]
                )  # catch value passed after OR statement
                filtered_data = [
                    row
                    for row in data
                    if condition_func(word_cond1, row)
                    or condition_func(word_cond2, row)
                ]
            else:
                word_cond = tuple_value(commands["where"])
                filtered_data = [row for row in data if condition_func(word_cond, row)]

            return filtered_data

    except:
        print("Error : Wrong argument near {}".format(tuple_value(commands["where"])))
        return False


def condition_func(condition, row):
    if condition.find("=") != -1 and (
        condition.find(">") == -1 and condition.find("<") == -1
    ):
        aux = condition.split("=")
        left = aux[0]
        right = aux[1]

        return row[left] == right

    elif condition.find(">") != -1 and condition.find("=") == -1:
        aux = condition.split(">")
        left = aux[0]
        right = aux[1]

        return int(row[left]) > int(right)

    elif condition.find("<") != -1 and condition.find("=") == -1:
        aux = condition.split("<")
        left = aux[0]
        right = aux[1]

        return int(row[left]) < int(right)

    elif condition.find(">") != -1 and condition.find("=") != -1:
        aux = condition.split(">=")
        left = aux[0]
        right = aux[1]

        return int(row[left]) >= int(right)

    elif condition.find("<") != -1 and condition.find("=") != -1:
        aux = condition.split("<=")
        left = aux[0]
        right = aux[1]

        return int(row[left]) <= int(right)
    else:
        print("Error : Wrong arguments near {}".format(condition))
        return False

def _orderby(data:list):
    clause = tuple_value(commands["order by"])
    if clause != None:
        if clause in data[0]:
            data.sort(key=lambda x:int(x[clause]))
            return data
        else:
            print("Error: Wrong arguments near {}".format(clause))
            return False
    else:
        return data

def _select(data: list):

    #filters aplication
    data = _where(data)
    data = _orderby(data)

    columns = tuple_value(commands["select"])

    if columns != None:
        try:
            if columns == "*":
                headers = list(data[0])
                print(headers)
                for row in data:
                    printable = []
                    for key in iter(row):
                        printable.append(row[key])
                    print(printable)

                return True
            else:
                columns = columns.split(",")

                # verifies if a columns typed is in the table
                for input_key in columns:
                    if input_key not in data[0]:
                        print("Error : {} didn't exists".format(input_key))
                        return False

                headers = columns
                print(headers)

                for row in data:
                    printable = []
                    for key in iter(row):
                        if key in headers:
                            printable.append(row[key])
                    print(printable)

                return True
        except:
            #No data printed, so do nothing
            return False
    else:
        print("Error : Wrong argument near SELECT")
        return False


def _update():
    return


def _insert():
    return


def _delete():
    return


# splits the query with it's respectively statements
# and treat accordingly
def parser(query: str):
    global commands

    commands = {
        "select": None,
        "update": None,
        "set": None,
        "insert": None,
        "delete": None,
        "into": None,
        "values": None,
        "from": None,
        "join": None,
        "on": None,
        "using": None,
        "where": None,
        "and": None,
        "or": None,
        "order by": None,
    }
    try:
        query = query.replace(", ", ",")
        query = query.replace(" ,", ",")
        query = query.replace(" =", "=")
        query = query.replace("= ", "=")
        query = query.replace(" >=",">=")
        query = query.replace(">= ",">=")
        query = query.replace(" <=","<=")
        query = query.replace("<= ","<=")
        query = query.replace(" >",">")
        query = query.replace("> ",">")
        query = query.replace(" <","<")
        query = query.replace("< ","<")
        query = query.replace("order by", "orderby")

        # splits sql command using space as separator
        query_list = query.split()

        # extract table in query
        if "from" in query_list:
            i = query_list.index("from")
            table = query_list[i + 1]
            commands["from"] = table, i
            # extract join argument
            if "join" in query_list:
                i = query_list.index("join")
                join_table = query_list[i + 1]
                commands["join"] = join_table, i
                if join_table in commands:
                    print("Error : Wrong argument near {}".format(join_table))
                    return False
                if "on" in query_list:
                    i = query_list.index("on")
                    join_column = query_list[i + 1]
                    commands["on"] = join_column, i
                    if join_column in commands:
                        print("Error : Wrong argument near {}".format(join_column))
                        return False
                elif "using" in query_list:
                    i = query_list.index("using")
                    join_column = query_list[i + 1]
                    commands["using"] = join_column, i
                    if join_column in commands:
                        print("Error : Wrong arguments near {}".format(join_column))
                        return False
                else:
                    print("Error : Wrong argument near  {}".format(join_table))
                    return False
        elif "update" in query_list:
            i = query_list.index("update")
            table = query_list[i + 1]
            commands["update"] = table, i
        elif "into" in query_list:
            i = query_list.index("into")
            table = query_list[i + 1]
            commands["into"] = table, i
        else:
            print("Error : Wrong argument near {}".format(table))
            return 0

        # verification if arguments is part of commands
        if table in commands:
            print("Error : wrong argument {}".format(table))
            return 0

        if "select" in query_list:
            i = query_list.index("select")
            columns = query_list[i + 1]
            commands["select"] = columns, i
        elif "update" in query_list:
            i = query_list.index("set")
            # TODO
        elif "insert" in query_list:
            i = query_list.index("values")
            # TODO
        elif "delete" in query_list:
            i = query_list.index()
            # TODO
        else:
            print("Error : unexpected")
            return False

        # catch where statement
        if "where" in query_list:
            i = query_list.index("where")
            clause = query_list[i + 1]
            commands["where"] = clause, i
        # catch and or statement
        if "and" in query_list:
            i = query_list.index("and")
            clause = query_list[i + 1]
            commands["and"] = clause, i
        elif "or" in query_list:
            i = query_list.index("or")
            clause = query_list[i + 1]
            commands["or"] = clause, i
        # catch order by
        if "orderby" in query_list:
            i = query_list.index("orderby")
            clause = query_list[i + 1]
            commands["order by"] = clause, i

    except:
        print("Error : Invalid query")
        return False

    data = _from()

    if tuple_value(commands["select"]):
        _select(data)
    elif tuple_value(commands["update"]):
        _update()
    elif tuple_value(commands["insert"]):
        _insert()
    elif tuple_value(commands["delete"]):
        _delete()
    


def check_existing_table(table: str, schema: str):
    path = catch_table_path(table, schema)
    return os.path.exists(path)


def catch_table_path(table: str, schema: str):
    path = (catch_schema_path(schema) + "/tables/{}.csv").format(table)
    return path


def check_existing_schema(schema):
    path = catch_schema_path(schema)
    return os.path.exists(path)


def catch_schema_path(schema: str):
    path = (os.getcwd() + "/schemas/{}").format(schema)
    return path


def create_schema(schema):
    path = catch_schema_path(schema)
    os.mkdir(path)
    os.mkdir(path + "/tables")


def data_import():
    server = None
    while not (server == "mysql" or server == "postgres"):
        print("Select the server (mysql or postgres)")
        server = input(">> ")
    if server == "mysql":
        mysql_handler.mysqlimport()
    elif server == "postgres":
        postgres_handler.postgresimport()
    return


def list_schemas():
    files = os.listdir(os.getcwd() + "/schemas")
    for it in files:
        printable = it.strip(".csv")
        print("@ " + printable)


def query():
    global schema

    retype = "y"
    while retype != "y" or retype != "n":
        if retype == "y":
            print("Select schema :")
            list_schemas()
            print()
            schema = input(">> ")
            print()
            if check_existing_schema(schema):
                retype_query = "y"
                while retype_query != "y" or retype_query != "n":
                    if retype_query == "y":
                        print("Type query : ")
                        query = input(">> ")
                        print()
                        parser(query)
                    elif retype_query == "n":
                        return True
                    print("re-type query? (y/n)")
                    retype_query = input(">> ")
            else:
                print("error : Schema not found in query_processor server")
        elif retype == "n":
            return True
        print("re-type schema ? (y/n)")
        retype = input(">> ")
    return True


def main():
    # takes query from user
    answer = None
    while not (answer == "i" or answer == "q"):
        print("Import or query? (i/q)")
        answer = input(">> ")
        print()
    if answer == "i":
        data_import()
    else:
        query()


if __name__ == "__main__":
    while True:
        main()
