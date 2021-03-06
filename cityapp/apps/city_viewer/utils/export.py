# -*- coding: utf8 -*-
#from __future__ import unicode_literals
from django.core import serializers
import os
import shutil
import sqlite3
from datetime import datetime
from string import Template
from django.conf import settings
from django.utils import simplejson
from django.template import loader
from filebrowser.sites import site
from cityapp.apps.city_viewer.models import Area,APPInfo,APPLike, OfflineMap, TripTip
#######################################################
#导出数据
topic_template = Template("""INSERT INTO "city_topic" VALUES('${id}','${name}','${desc}','${cover_pic}',${weight});""")
#place_template = Template("""INSERT INTO "city_place" VALUES('${id}','${zh_name}','${en_name}',${category},${in_area_id},'${longitude}','${latitude}','${short_desc}','${full_desc}',${fit_time},'${open_time}','${address}','${traffic}','${price}','${tel}','${website}','${tips}','${modified_at}'); """)
place_template = Template("""INSERT INTO "city_place" VALUES('${id}','${zh_name}','${en_name}',${category},'${longitude}','${latitude}','${short_desc}',${fit_time},'${info}');""")
place_in_topic_template = Template("""INSERT INTO "city_place_in_topics" VALUES('${id}','${place_id}','${topic_id}');""");
picture_template = Template("""INSERT INTO "city_picture" VALUES('${id}','${file_name}','${url}','${desc}','${in_place_id}','${modified_at}');""")
meta_template = Template("""INSERT INTO "city_meta" VALUES('${key}', '${value}');""")

def handle_single_quote(**dict):
    for key, value in dict.items():
        #print key,value
        if isinstance(value, basestring):
             dict[key] = value.replace("'","''")
    return dict

def generate_place_info(place):
    info = {}
    if place.full_desc:
        info.update({"description":place.full_desc})
    if place.address:
        info.update({"address":place.address})
    if place.open_time:
        info.update({"openTime":place.open_time})
    if place.traffic:
        info.update({"arriveMethod":place.traffic})
    if place.website:
        info.update({"website":place.website})
    if place.price:
        info.update({"ticketInfo":place.price})
    if place.tel:
        info.update({"phoneNumber":place.tel})
    if place.tips:
        info.update({"tips":place.tips})
    return simplejson.dumps(info)

def export_city_sql(name, sql_schema='db_schema.sql'):
    try:
        area = Area.objects.get(en_name=name)
    except Area.DoesNotExist:
        pass
    else:
        db_dir_path = os.path.join(settings.STATIC_ROOT, 'city_db/')
        src = db_dir_path + sql_schema
        dst = db_dir_path + name + '.sql'
        shutil.copyfile(src, dst)
        with open(dst, 'a') as fp:
            #meta info
            meta = []
            meta.append({"key":"app_vision", "value":u"途客圈是一群热爱旅行的“途客”组成的团队，每个人心怀环游世界的梦想。##正如你所看到的，在途客圈城市指南系列App里，每一位途客都可以是一个城市指南的主人，把自己的发现、感觉以不同的主题呈现给大家。相信你也有丰富的旅行经历，那为什么不尝试编写一个属于自己的城市指南与更多的途客共享呢？联系我们吧，你会发现做这一切很简单！##愿途客圈成为你旅行路上的一个家，在这里你可以和其他途客们分享精彩的旅行人生，发现更大的世界。"})
            meta.append({"key":"author_name", "value":area.author.get_profile().name})
            meta.append({"key":"author_desc", "value":area.author_desc})
            meta.append({"key":"liked", "value":"no"})
            meta.append({"key":"firsttime", "value":"no"})
            meta.append({"key":"hotel_link", "value":area.hotel_link})
            meta.append({"key":"links", "value":""})
            meta.append({"key":"datetime", "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            try:
                app_info = APPInfo.objects.get(area=area)
                meta.append({"key":"rating_url", "value":app_info.link})
                meta.append({"key":"latest_ver","value":app_info.latest_ver})
                meta.append({"key":"asid", "value":app_info.asid})
            except APPInfo.DoesNotExist:
                pass

            try:
                meta.append({"key":"liked_num", "value":100 + APPLike.objects.liked_num(area)})
            except APPLike.DoesNotExist:
                pass

            try:
                offline = OfflineMap.objects.get(in_area=area)
                meta.append({"key":"map_size", "value": offline.file.size})
                meta.append({"key":"map_center", "value": offline.center})
                meta.append({"key":"map_url", "value": offline.file.url})
                meta.append({"key":"map_zoom", "value": offline.zoom})
                meta.append({"key":"map_min_zoom", "value": offline.min_zoom})
                meta.append({"key":"map_max_zoom", "value": offline.max_zoom})
                meta.append({"key":"map_downloaded", "value": "no"})
            except OfflineMap.DoesNotExist:
                pass

            for info in meta:
                line = meta_template.safe_substitute(info).encode('utf-8')
                print line
                fp.write('%s\n' % line)
            #Topic
            topics = area.topic_set.all()
            count = 0
            for topic in topics:
                topic.__dict__ = handle_single_quote(**topic.__dict__)
                line = topic_template.substitute(**topic.__dict__).encode('utf-8')
                fp.write('%s\n' % line)
                for p in topic.place_set.all():
                    count += 1
                    line = place_in_topic_template.substitute(id=count, place_id=p.id, topic_id=topic.id)
                    fp.write('%s\n' % line)
            places = area.place_set.all()
            for place in places:
                place.__dict__ = handle_single_quote(**place.__dict__)
                info = generate_place_info(place)
                #print info
                line = place_template.substitute(id=place.id, zh_name=place.zh_name, en_name=place.en_name, \
                    category=place.category, longitude=place.longitude, latitude=place.latitude, \
                    fit_time = place.fit_time, short_desc=place.short_desc, info=info).encode('utf-8')
                fp.write('%s\n' % line)
                for pic in place.picture_set.all():
                    pic.__dict__ = handle_single_quote(**pic.__dict__)
                    line = picture_template.substitute(**pic.__dict__).encode('utf-8')
                    fp.write('%s\n' % line)
            fp.write('COMMIT;')
        fp.close()
#######################################################
#导出更新的数据
def sstrip(str):
    if len(str) > 2:
        return str[1:-1] + ','
    else:
        return ''

def json(str):
    return '[' + str[:-1] + ']'

def dump_data(queryset):
    #Area
    areas_data = sstrip(serializers.serialize("json", queryset))
    for area in queryset:
        #AppInfo
        appinfo = area.appinfo_set.all()
        appinfo_data = sstrip(serializers.serialize("json", appinfo))
        #OfflineMap
        om = area.offlinemap_set.all()
        om_data = sstrip(serializers.serialize("json", om))
        #Tips
        tips = area.triptip_set.all()
        tips_data = sstrip(serializers.serialize("json", tips))
        #Topic
        topics = area.topic_set.all()
        topic_data = sstrip(serializers.serialize("json", topics))
        #Place
        places = area.place_set.all()
        place_data = sstrip(serializers.serialize("json", places))
        #Pictures
        pictures_data = ''
        for place in places:
            pictures = place.picture_set.all()
            pictures_data += sstrip(serializers.serialize("json", pictures))
        area_data = topic_data + place_data + pictures_data + tips_data + appinfo_data + om_data
        areas_data += area_data
    export_path = os.path.join(settings.STATIC_ROOT, 'cities/', "data.json")
    with open(export_path, 'w') as fp:
        fp.write(json(areas_data).encode('utf-8'))
    fp.close()
#######################################################
#导出单个城市的数据
def export_city_db(name):
    db_dir_path = os.path.join(settings.STATIC_ROOT, 'city_db/')
    export_path = os.path.join(settings.STATIC_ROOT, 'cities/', name)
    #检查目录
    if not os.path.isdir(export_path):
        export_path = os.path.join(settings.STATIC_ROOT, 'cities/')
    #确定路径
    sql_path = os.path.join(db_dir_path, name + '.sql')
    db_path = os.path.join(export_path, name + '.db')
    if os.path.isfile(db_path):
        os.remove(db_path)
    #生成DB
    with open(sql_path, 'r') as fp:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        cursor.executescript(fp.read())
        connection.commit()
        cursor.close()
    #删除sql脚本
    os.remove(sql_path)
    fp.close()

def export_city_tips_html(name):
    export_path = os.path.join(settings.STATIC_ROOT, 'cities/', name)
    html_path = os.path.join(export_path, 'tips.html')
    if not os.path.isdir(export_path):
        export_path = os.path.join(settings.STATIC_ROOT, 'cities/')
        html_path = os.path.join(export_path, 'tips_%s.html' % name)

    template_name = 'city_viewer/triptips.html'
    tips = TripTip.objects.filter(in_area__en_name=name)
    body = loader.render_to_string(template_name, {'tips': tips})
    body.replace('/static/css/images/','')

    with open(html_path, 'w') as fp:
        fp.write(body.encode('utf-8'))
    fp.close()

#######################################################
#重新整理Token
def export_device_token():
    from cityapp.apps.city_viewer.models.appinfo import APPDeviceToken
    from cityapp.apps.ios_notifications.models import DeviceToken, APNService
    tokens = APPDeviceToken.objects.all()
    for token in tokens:
        print token.token
        services = APNService.objects.filter(app=token.app)
        if services.exists():
            service = services.get()
        else:
            service = APNService(app=token.app)
            service.save()

        new_token = DeviceToken(service=service, device=token.device, token=token.token, is_active=True)
        new_token.save()

#######################################################
