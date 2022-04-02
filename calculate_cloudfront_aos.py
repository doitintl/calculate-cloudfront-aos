import datetime
import argparse
import botocore
import boto3
import json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate Amazon CloudFront AOS using Cost Explorer API.')
    parser.add_argument('--month', help='specify month')
    parser.add_argument('--year', help='specify year')
    parser.add_argument('--profile', help='specify aws profile from ~/.aws/credentials')
    parser.add_argument('--output', help='json or text')

    args = parser.parse_args()

    today = datetime.datetime.today()
    month = int(args.month) if args.month else today.month
    year = int(args.year) if args.year else today.year
    profile = args.profile if args.profile else 'default'
    output_format = args.output if args.output else 'text'

    first_day_of_month = datetime.datetime(year, month, 1).date()
    current_day_of_month = datetime.datetime(year, month, today.day).date()
    # Cost Explorer API TimePeriod end date is exclusive, adding 1 more day to end date
    end_date = (first_day_of_month.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    if month == today.month:
        end_date = today.date() + datetime.timedelta(days=1)
    first_day_of_month = str(first_day_of_month)
    end_date = str(end_date)
    try:
        session = boto3.session.Session(profile_name=profile)
        client = session.client('ce', region_name='us-east-1')

        output = client.get_cost_and_usage(TimePeriod={'Start': first_day_of_month, 'End': end_date},
                                           Metrics=['USAGE_QUANTITY'], Granularity='MONTHLY',
                                           GroupBy=[{'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}], Filter={'Dimensions':
                                            {'Key': 'SERVICE', 'Values': ['Amazon CloudFront']}})
    except botocore.exceptions.ClientError as error:
        raise error
    #print(output)
    data_transfer_in_kb = []
    requests = []
    for k in output['ResultsByTime'][0]['Groups']:
        if 'DataTransfer-Out-Bytes' in k['Keys'][0]:
            data_transfer_in_kb.append(float(k['Metrics']['UsageQuantity']['Amount']))
        if '-Requests-Tier' in k['Keys'][0]:
            requests.append(float(k['Metrics']['UsageQuantity']['Amount']))
    data_transfer_in_kb = sum(data_transfer_in_kb) * 1048576
    requests = sum(requests)
    try:
        aos = round(data_transfer_in_kb / requests, 2)
        if output_format == 'json':
            print(json.dumps({'message': f'For AWS Profile {profile}, Account AOS for date {month}/{year} is: {aos}Kb', 'aos': aos}))
        else:
            print(f'For AWS Profile {profile}, Account AOS for date {month}/{year} is: {aos}Kb')
    except ZeroDivisionError:
        error_message = 'Cost explorer API returned 0 for one of the usage types (data transfer or requests), this is most likely because you run the report at the begging of the month, please adjust the dates using --month or --year parameters'
        if output_format == 'json':
            print(json.dumps({'message': error_message, 'aos': ''}))
        else:
            print(error_message)
