import requests
from openhumans.models import OpenHumansMember
from celery import shared_task
import io
import pandas
from .helpers import generate_csv


@shared_task(bind=True)
def foobar(self):
    print('Request: {0!r}'.format(self.request))


@shared_task
def process_batch(fname, oh_id):
    print('task processing {}'.format(oh_id))
    oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
    metrics = get_metrics_batch(oh_member, fname)
    if type(metrics) == list:
        print('batch is list of metrics')
        # now iterate through each metric in the batch
        for metric in metrics:
            # is any data for this metric in this batch?
            if len(metric['data']) > 0:
                metric_name = metric['name']
                print('processing {}'.format(metric_name))
                existing_metric_data, old_metric_file_id = get_existing_metric(oh_member, metric_name)
                batch_df = pandas.DataFrame.from_dict(metric['data'])
                for i in metric.keys():
                    if i != 'data':
                        batch_df[i] = metric[i]
                if metric_name == 'high_heart_rate_notifications':
                    batch_df = batch_df.drop(columns=['heartRate','heartRateVariation'])
                if type(existing_metric_data) == pandas.core.frame.DataFrame:
                    batch_df = pandas.concat(
                        [existing_metric_data, batch_df], sort='True'
                        ).reset_index(drop=True).drop_duplicates()
                batch_df = batch_df.sort_values('date')
                str_io = io.StringIO()
                batch_df.to_csv(str_io, index=False, encoding='utf-8')
                str_io.flush()
                str_io.seek(0)
                oh_member.upload(
                    stream=str_io, filename=metric_name+'.csv',
                    metadata={
                        'description': '{} data from Apple Health'.format(
                            metric_name),
                        'tags': ['apple health', metric_name,
                                 'processed', 'CSV']})
                oh_member.delete_single_file(file_basename=fname)
                if old_metric_file_id:
                    oh_member.delete_single_file(file_id=old_metric_file_id)
    else:
        print('batch is not dict')
        oh_member.delete_single_file(file_basename=fname)


def get_metrics_batch(oh_member, fname):
    for f in oh_member.list_files():
        if f['basename'] == fname:
            try:
                data = requests.get(f['download_url']).json()
                return data
            except:
                oh_member.delete_single_file(f['id'])
                return []


def get_existing_metric(oh_member, metric_name):
    for f in oh_member.list_files():
        if f['basename'] == metric_name+'.csv':
            print('get {} file'.format(metric_name))
            data = requests.get(f['download_url']).content
            print('got data')
            data = pandas.read_csv(io.StringIO(
                data.decode('utf-8', errors='ignore')))
            print('read CSV')
            return data, f['id']
    return None, ''


def get_date(batch):
    location = batch['locations'][0]  # get first location entry
    timestamp = location['properties']['timestamp'][:7]  # extract year-month
    return timestamp
