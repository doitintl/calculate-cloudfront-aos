from datetime import datetime
import argparse
import boto3
import json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate Amazon CloudFront AOS using Cost Explorer API.')
    parser.add_argument('--month', help='specify month')
    parser.add_argument('--year', help='specify year')
    parser.add_argument('--aws-profile', help='specify aws profile')
    parser.add_argument('--output', help='json or text')

    args = parser.parse_args()

    today = datetime.today()
    month = int(args.month) if args.month else today.month
    year = int(args.year) if args.year else today.year
    aws_profile = args.aws_profile if args.aws_profile else 'default'
    output_format = args.output if args.output else 'text'

    first_day_of_month = str(datetime(year, month, 1).date())
    current_day_of_month = str(datetime(year, month, today.day).date())

    session = boto3.session.Session(profile_name=aws_profile)
    client = session.client('ce', region_name='us-east-1')

    output = client.get_cost_and_usage(TimePeriod={'Start': first_day_of_month, 'End': current_day_of_month},
                                       Metrics=['USAGE_QUANTITY'], Granularity='MONTHLY',
                                       GroupBy=[{'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}], Filter={'Dimensions':
                                        {'Key': 'SERVICE', 'Values': ['Amazon CloudFront']}})

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
            print(json.dumps({'message': f'For AWS Profile {aws_profile}, Account AOS for date {month}/{year} is: {aos}Kb', 'aos': aos}))
        else:
            print(f'For AWS Profile {aws_profile}, Account AOS for date {month}/{year} is: {aos}Kb')
    except ZeroDivisionError:
        error_message = 'Cost explorer API returned 0 for one of the usage types (data transfer or requests), this is most likely because you run the report at the begging of the month, please adjust the dates using --month or --year parameters'
        if output_format == 'json':
            print(json.dumps({'message': error_message, 'aos': ''}))
        else:
            print(error_message)
