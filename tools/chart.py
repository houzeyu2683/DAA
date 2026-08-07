import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def draw_scatter_plot(
    database_path: str,
    table_name: str,
    x_column_name: str,
    y_column_name: str,
    image_path: str,
) -> dict:
    """從指定資料表讀取兩個欄位,畫出散佈圖並存檔。"""

    database_path = database_path.strip('"').strip("'")
    table_name = table_name.strip('"').strip("'")
    x_column_name = x_column_name.strip('"').strip("'")
    y_column_name = y_column_name.strip('"').strip("'")
    image_path = image_path.strip('"').strip("'")

    connection = duckdb.connect(database=database_path, read_only=True)
    data = connection.execute(
        f"SELECT {x_column_name}, {y_column_name} FROM {table_name}"
    ).fetchdf()
    connection.close()

    plt.figure()
    plt.scatter(data[x_column_name], data[y_column_name])
    plt.xlabel(x_column_name)
    plt.ylabel(y_column_name)
    plt.savefig(image_path)
    plt.close()

    return {"image_path": image_path}
