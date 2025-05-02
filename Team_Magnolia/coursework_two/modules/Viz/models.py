# models.py
import os
import json
from pymongo import MongoClient

class DataLoader:
    def __init__(self, mode="json", json_path=None, mongo_uri=None, db_name=None, collection_name=None):
        """
        mode: "json" 或 "mongo"
        如果是 json，必须给 json_path
        如果是 mongo，必须给 mongo_uri, db_name, collection_name
        """
        self.mode = mode
        self.json_path = json_path
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.collection_name = collection_name

        if self.mode == "json":
            if not json_path:
                raise ValueError("JSON模式必须提供json_path")
            self.data = self.load_json()
        elif self.mode == "mongo":
            if not all([mongo_uri, db_name, collection_name]):
                raise ValueError("Mongo模式必须提供mongo连接信息")
            self.client = MongoClient(mongo_uri)
            self.collection = self.client[db_name][collection_name]
        else:
            raise ValueError("模式只支持 'json' 或 'mongo'")

    def load_json(self):
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"找不到JSON文件: {self.json_path}")
        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_all_records(self):
        if self.mode == "json":
            return self.data
        elif self.mode == "mongo":
            return list(self.collection.find({}))

    def search_companies(self, keyword):
        keyword = keyword.lower()
        if self.mode == "json":
            return sorted({rec["company_name"] for rec in self.data if keyword in rec.get("company_name", "").lower()})
        else:
            pipeline = [
                {"$match": {"company_name": {"$regex": keyword, "$options": "i"}}},
                {"$group": {"_id": "$company_name"}},
                {"$sort": {"_id": 1}}
            ]
            return [doc["_id"] for doc in self.collection.aggregate(pipeline)]

    def build_thematic_area_choices(self):
        records = self.get_all_records()
        thematic_area_choices = {}
        for rec in records:
            area = rec.get("thematic_area", "Unknown")
            ind = rec.get("indicator_id")
            thematic_area_choices.setdefault(area, [])
            if ind and ind not in thematic_area_choices[area]:
                thematic_area_choices[area].append(ind)
        return thematic_area_choices

    def extract_year_value_map(self, rec, selected_years):
        rec_years = rec.get('years') or []
        nums = rec.get('values_numeric') or []
        txts = rec.get('values_text') or []

        year_map = {}
        for y in selected_years:
            if y in rec_years:
                idx = rec_years.index(y)
                val = nums[idx] if idx < len(nums) and nums[idx] is not None else (
                      txts[idx] if idx < len(txts) else None
                )
            else:
                val = None
            year_map[y] = val
        return year_map
