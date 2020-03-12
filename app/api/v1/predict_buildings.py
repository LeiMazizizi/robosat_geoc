﻿from sqlalchemy import or_
from app.models.base import queryBySQL, db as DB
from app.libs.redprint import Redprint
from app.models.predict_buildings import PredictBuildings
from flask import jsonify
from flask import request
from geomet import wkb

import json

api = Redprint('predict_buildings')


@api.route("", methods=['GET'])
def onegeojson():
    result = {
        "code": 1,
        "data": None,
        "msg": "ok"
    }
    task_id = request.args.get("task_id")
    if not task_id:
        result["code"] = 0
        result["msg"] = "task_id缺失"
        return jsonify(result)
    sql = '''select * from "BUIA" where gid in (select a.gid from predict_buildings as a where task_id ={task_id}) '''
    queryData = queryBySQL(sql.format(task_id=task_id))
    if not queryData:
        result["code"] = 0
        result["msg"] = "查询语句有问题"
        return jsonify(result)
    row = queryData.fetchall()
    result["data"] = row

    return jsonify(result)


@api.route("/<gid>", methods=['GET'])
def get(gid):
    result = {
        "code": 1,
        "data": None,
        "msg": "ok"
    }
    sql = '''select st_asgeojson(geom) as geojson from predict_buildings WHERE gid ={gid}'''
    queryData = queryBySQL(sql.format(gid=gid))
    if not queryData:
        result["code"] = 0
        result["msg"] = "查询语句有问题"
        return jsonify(result)
    if queryData.rowcount == 0:
        result["code"] = 0
        result["msg"] = "未查询到内容"
        return jsonify(result)
    row = queryData.fetchone()
    if row['geojson']:
        result["data"] = json.loads(row["geojson"])
    else:
        result['data'] = None
    return jsonify(result)


@api.route('', methods=['POST'])
def create_buildings(geojsonObj):
    result = {
        "code": 1,
        "data": None,
        "msg": "ok"
    }
    # check params
    if request.json:
        paramsDic = request.json
        params = json.loads(json.dumps(paramsDic))
        geojson = params['geojson']
    else:
        geojson = geojsonObj

    buildings = []
    for feature in geojson["features"]:
        # featureDump = json.dumps(feature)
        # newFeat = '{"type":"FeatureCollection","features":['+featureDump+']}'

        # newFeature = json.loads(newFeat)
        newBuild = PredictBuildings()
        newBuild.task_id = feature["properties"]['task_id']
        newBuild.extent = feature["properties"]['extent']
        newBuild.user_id = feature["properties"]['user_id']
        buildings.append(newBuild)

    # insert into
    with DB.auto_commit():
        DB.session.bulk_save_objects(buildings)
        return jsonify(result)


@api.route('', methods=['POST'])
def update_buildings():
    result = {
        "code": 1,
        "data": None,
        "msg": "ok"
    }
    # check params
    if not request.json:
        result['code'] = 0
        result['msg'] = 'miss params.'
        return jsonify(result)

    paramsDic = request.json
    params = json.loads(json.dumps(paramsDic))

    if 'status' not in params:
        result['code'] = 0
        result['msg'] = 'miss status.'
        return jsonify(result)

    if 'ids' not in params and 'task_id' not in params:
        result['code'] = 0
        result['msg'] = 'miss ids or task_id.'
        return jsonify(result)

    if 'ids' in params and 'task_id' in params:
        result['code'] = 0
        result['msg'] = 'both have ids and task_id.'
        return jsonify(result)

    status = params['status']

    def updateBuildByIds(ids):
        for gid in ids:
            build = PredictBuildings.query.filter_by(gid=gid).first_or_404()
            if not build:
                continue
            build.status = status
            with DB.auto_commit():
                DB.session.add(build)

    if "ids" in params:
        ids = params['ids']
        if not isinstance(ids, list):
            result['code'] = 0
            result['msg'] = 'ids not list type.'
            return jsonify(result)
        updateBuildByIds(ids)

    if "task_id" in params:
        task_id = params['task_id']
        # builds = PredictBuildings.query.filter_by(task_id=task_id)
        # if not builds:
        #     result['code'] = 0
        #     result['msg'] = 'task id not found'
        #     return jsonify(result)
        # for build in builds:
        #     build.status = status
        #     DB.session.bulk_save_objects(builds)
        sql = '''SELECT gid, task_id, extent, user_id, state, status from predict_buildings WHERE task_id = {task_id}'''
        queryData = queryBySQL(sql.format(task_id=task_id))
        if not queryData:
            result["code"] = 0
            result["msg"] = "查询语句有问题"
            return jsonify(result)
        rows = queryData.fetchall()
        ids = []
        for row in rows:
            gid = row.gid
            ids.append(gid)
        updateBuildByIds(ids)
    return jsonify(result)


def insert_buildings(geojsonObj):
    if not geojsonObj:
        return False

    # geojson to buildings array
    buildings = []
    for feature in geojsonObj["features"]:
        geometry = feature['geometry']
        newBuild = PredictBuildings()
        newBuild.task_id = feature["properties"]['task_id']
        newBuild.extent = feature["properties"]['extent']
        newBuild.user_id = feature["properties"]['user_id']
        newBuild.geom = wkb.dumps(geometry).hex()
        buildings.append(newBuild)

    # insert into
    with DB.auto_commit():
        DB.session.bulk_save_objects(buildings)
        return True
