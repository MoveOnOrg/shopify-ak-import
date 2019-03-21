import argparse
import csv
from datetime import date, datetime, timedelta
import requests
import StringIO

class ShopifyAKImporter:

    def __init__(self, settings):
        self.settings = settings

    def get_count(self, min_date=None, since_id=None):

        query = 'status=any'

        if min_date:
            # Specific date if provided
            min_date = datetime.strptime(min_date, "%Y-%m-%d")
            max_date = min_date + timedelta(days=1)
            query += '&created_at_min=%sT00:00:00-05:00&created_at_max=%sT00:00:00-05:00' % (datetime.strftime(min_date, "%Y-%m-%d"), datetime.strftime(max_date, "%Y-%m-%d"))
        elif since_id:
            # Since ID if provided
            query += '&since_id=%s' % since_id
        else:
            # Default to yesterday
            max_date = date.today()
            min_date = max_date + timedelta(days=-1)
            query += '&created_at_min=%sT00:00:00-05:00&created_at_max=%sT00:00:00-05:00' % (datetime.strftime(min_date, "%Y-%m-%d"), datetime.strftime(max_date, "%Y-%m-%d"))

        url = 'https://%s:%s@%s.myshopify.com/admin/orders/count.json?%s' % (
            self.settings.SHOPIFY_API_KEY,
            self.settings.SHOPIFY_PASSWORD,
            self.settings.SHOPIFY_SUBDOMAIN,
            query
        )

        return requests.get(url).json().get('count', 0)


    def get_url(self, min_date=None, since_id=None, page=1):
        """
        Generate a Shopify order request URL from given filters
        """
        query = 'page=%s&limit=250&status=any' % page

        if min_date:
            # Specific date if provided
            min_date = datetime.strptime(min_date, "%Y-%m-%d")
            max_date = min_date + timedelta(days=1)
            query += '&created_at_min=%sT00:00:00-05:00&created_at_max=%sT00:00:00-05:00' % (datetime.strftime(min_date, "%Y-%m-%d"), datetime.strftime(max_date, "%Y-%m-%d"))
        elif since_id:
            # Since ID if provided
            query += '&since_id=%s' % since_id
        else:
            # Default to yesterday
            max_date = date.today()
            min_date = max_date + timedelta(days=-1)
            query += '&created_at_min=%sT00:00:00-05:00&created_at_max=%sT00:00:00-05:00' % (datetime.strftime(min_date, "%Y-%m-%d"), datetime.strftime(max_date, "%Y-%m-%d"))

        return 'https://%s:%s@%s.myshopify.com/admin/orders.json?%s' % (
            self.settings.SHOPIFY_API_KEY,
            self.settings.SHOPIFY_PASSWORD,
            self.settings.SHOPIFY_SUBDOMAIN,
            query
        )


    def get_csv(self, url=None):
        """
        Generate CSV file from a URL
        """
        if url is None:
            url = self.get_url()
        # Get orders
        orders = requests.get(url).json().get('orders', [])
        # Filter out refunds
        orders = [order for order in orders if order.get('financial_status', '') != 'refunded']
        # Write orders to CSV
        output_file = StringIO.StringIO()
        csv_writer = csv.writer(output_file)
        csv_writer.writerow([
            'donation_import_id', 'email', 'donation_date',
            'donation_amount', 'first_name', 'last_name',
            'address1', 'address2', 'city',
            'postal', 'state', 'country',
            'phone', 'user_occupation', 'user_employer',
            'source', 'donation_payment_account',
            'action_occupation', 'action_employer'
        ])
        for order in orders:
            # Prepare data
            donation_import_id = 'shopify-' + str(order.get('order_number', ''))
            email = order.get('email', '')
            donation_date = order.get('created_at', '')
            donation_amount = order.get('total_price', '')
            first_name = order.get('customer', {}).get('first_name', '')
            last_name = order.get('customer', {}).get('last_name', '')
            address1 = order.get('billing_address', {}).get('address1', '')
            address2 = order.get('billing_address', {}).get('address2', '')
            city = order.get('billing_address', {}).get('city', '')
            postal = order.get('billing_address', {}).get('zip', '')
            state = order.get('billing_address', {}).get('province_code', '')
            country = order.get('billing_address', {}).get('country_code', '')
            phone = order.get('billing_address', {}).get('phone', '')
            notes = order.get('note_attributes', [])
            occupations = [note for note in notes if note.get('name', '') == 'Occupation']
            user_occupation = ''
            if len(occupations):
                user_occupation = occupations[0].get('value', '')
            employers = [note for note in notes if note.get('name', '') == 'Employer']
            user_employer = ''
            if len(employers):
                user_employer = employers[0].get('value', '')

            # Write CSV row
            csv_writer.writerow([
                donation_import_id, email, donation_date,
                donation_amount, first_name.encode('utf-8'), last_name.encode('utf-8'),
                address1.encode('utf-8'), address2, city.encode('utf-8'),
                postal, state, country,
                phone, user_occupation.encode('utf-8'), user_employer.encode('utf-8'),
                self.settings.AK_SOURCE, self.settings.AK_PAYMENT_ACCOUNT,
                user_occupation.encode('utf-8'), user_employer.encode('utf-8')
            ])

        return output_file

    def import_to_ak(self, csv_file):
        """
        Import given CSV file into ActionKit
        """
        url  = self.settings.AK_API_BASE_URL + 'upload/'
        result = requests.post(url,
            files={'upload': StringIO.StringIO(csv_file.getvalue())},
            data={'page': self.settings.AK_IMPORT_PAGE, 'autocreate_user_fields': 0},
            auth=(self.settings.AK_USER, self.settings.AK_PASSWORD)
        )
        return result

def main():

    import settings

    parser = argparse.ArgumentParser(description='Import shopify orders into ActionKit.')
    parser.add_argument('--date', dest='min_date', help='date of orders to import')
    parser.add_argument('--since', dest='since_id', help='ID after which to import')
    parser.add_argument('--url', dest='url_only', help='only output URL', action='store_const', const=True, default=False)
    parser.add_argument('--csv', dest='csv_only', help='only output CSV', action='store_const', const=True, default=False)
    parser.add_argument('--count', dest='count_only', help='only output count', action='store_const', const=True, default=False)


    args = parser.parse_args()

    importer = ShopifyAKImporter(settings)

    count = importer.get_count(args.min_date, args.since_id)

    if args.count_only:
        print(count)
    else:

        imported = 0
        page = 1

        while imported <= count:

            url = importer.get_url(args.min_date, args.since_id, page)

            if args.url_only:
                # Output URL without doing anything (for checking data in browser)
                print(url)
            else:
                csv_file = importer.get_csv(url)
                if args.csv_only:
                    # Output CSV
                    contents = csv_file.getvalue()
                    print(contents)
                else:
                    # Send to ActionKit
                    result = importer.import_to_ak(csv_file)
                csv_file.close()

            imported += 250
            page += 1


def aws_lambda(event, context):
    main()

if __name__ == '__main__':
    main()
