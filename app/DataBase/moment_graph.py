import os
import sqlite3
import time

import networkx as nx
import pandas as pd
import pywxdump
from pyvis.network import Network


def get_username_to_remark_map(db_path):
    conn = sqlite3.connect(db_path)
    try:
        name = pd.read_sql("SELECT userName, nickName, remark FROM Contact", conn)
        name.dropna(inplace=True)
        name = name[name["Remark"] != ""]
        return dict(zip(name["UserName"], name["Remark"]))
    finally:
        conn.close()

def timestamp_to_time(timestamp):
    local_time = time.localtime(timestamp)
    return time.strftime("%Y-%m-%d %H:%M:%S", local_time)

def get_table_as_dataframe(db_path, table_name):
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql(f"SELECT * FROM {table_name};", conn)
    except sqlite3.Error as e:
        print(f"查询表数据时出错: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def generate_comment_network():
    try:
        wx_data = pywxdump.get_wx_info()[0]
        yourself = wx_data["wxid"]

        micro_msg_db_path = "./app/DataBase/Msg/MicroMsg.db"
        sns_db_path = "./app/DataBase/Msg/Sns.db"

        username2remark = get_username_to_remark_map(micro_msg_db_path)

        def id_to_name(id):
            return username2remark.get(id, id)

        feeds_df = get_table_as_dataframe(sns_db_path, "FeedsV20")
        comments_df = get_table_as_dataframe(sns_db_path, "CommentV20")

        comments_df["FromUserName"] = comments_df["FromUserName"].apply(id_to_name)
        feeds_df["UserName"] = feeds_df["UserName"].apply(id_to_name)

        feed_comments = []
        for _, row in feeds_df.iterrows():
            feed_id = row["FeedId"]
            if feed_id in comments_df["FeedId"].values:
                comments = comments_df[comments_df["FeedId"] == feed_id]["FromUserName"].to_list()
                feed_comments.append([row["UserName"], comments])
        
        feeds2comments = pd.DataFrame(feed_comments, columns=["UserName", "Comments"])

        if os.path.exists("graph.gexf"):
            G = nx.read_gexf("graph.gexf")
        else:
            G = nx.Graph()

        for _, row in feeds2comments.iterrows():
            poster = row["UserName"]
            commenters = row["Comments"]
            G.add_node(poster)
            for commenter in commenters:
                G.add_node(commenter)
                G.add_edge(commenter, poster)
        
        if G.has_node(yourself):
            G.remove_node(yourself)
            
        nx.write_gexf(G, "graph.gexf")

        net = Network(notebook=True, directed=False, height="750px", width="100%")
        net.from_nx(G)
        net.show_buttons(filter_=["physics"])
        net.show("comment_network.html")
        
        return "评论网络图生成成功，请查看 comment_network.html"
    except Exception as e:
        return f"生成失败: {e}"

if __name__ == '__main__':
    print(generate_comment_network())