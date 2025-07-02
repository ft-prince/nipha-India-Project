# management/commands/bom_helper.py
from django.core.management.base import BaseCommand
from screen_app.models import BOMItem, BOMTemplate, BOMTemplateItem, Product, AssemblyStage
from django.db import transaction
import json

class Command(BaseCommand):
    help = 'BOM management helper - add items, create templates, bulk operations'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['add_item', 'create_template', 'list_items', 'list_templates', 'preview_bom', 'bulk_add'],
            help='Action to perform'
        )
        parser.add_argument('--item-code', help='Item code for new item')
        parser.add_argument('--description', help='Item description')
        parser.add_argument('--part-number', help='Part number')
        parser.add_argument('--unit', default='NO.', help='Unit of measure (NO., KGS, GM, etc.)')
        parser.add_argument('--cost', type=float, help='Cost per unit')
        parser.add_argument('--supplier', help='Supplier name')
        
        parser.add_argument('--product-code', default='BRG-40K', help='Product code')
        parser.add_argument('--template-name', help='Template name')
        parser.add_argument('--bom-type', choices=['SINGLE_UNIT', 'BATCH_50', 'SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY'], help='BOM type')
        parser.add_argument('--stage', choices=['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY'], help='Assembly stage')
        parser.add_argument('--displays', default='1,2,3', help='Display screens (comma-separated: 1,2,3)')
        
        parser.add_argument('--template-id', type=int, help='Template ID for preview')
        parser.add_argument('--quantity', type=int, default=1, help='Quantity for BOM preview')
        
        parser.add_argument('--json-file', help='JSON file for bulk operations')

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'add_item':
            self.add_item(options)
        elif action == 'create_template':
            self.create_template(options)
        elif action == 'list_items':
            self.list_items()
        elif action == 'list_templates':
            self.list_templates()
        elif action == 'preview_bom':
            self.preview_bom(options)
        elif action == 'bulk_add':
            self.bulk_add_items(options)

    def add_item(self, options):
        """Add a single BOM item"""
        required_fields = ['item_code', 'description', 'part_number']
        missing_fields = [field.replace('_', '-') for field in required_fields if not options.get(field)]
        
        if missing_fields:
            self.stdout.write(
                self.style.ERROR(f'Missing required fields: {", ".join(missing_fields)}')
            )
            return

        try:
            item, created = BOMItem.objects.get_or_create(
                item_code=options['item_code'],
                defaults={
                    'item_description': options['description'],
                    'part_number': options['part_number'],
                    'unit_of_measure': options['unit'],
                    'cost_per_unit': options.get('cost'),
                    'supplier': options.get('supplier'),
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created item: {item.item_code} - {item.item_description}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Item already exists: {item.item_code}')
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error creating item: {str(e)}'))

    def create_template(self, options):
        """Create a BOM template"""
        if not options.get('template_name') or not options.get('bom_type'):
            self.stdout.write(self.style.ERROR('❌ Template name and BOM type are required'))
            return

        try:
            product = Product.objects.get(code=options['product_code'])
        except Product.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Product {options["product_code"]} not found'))
            return

        stage = None
        if options.get('stage'):
            try:
                stage = AssemblyStage.objects.get(name=options['stage'])
            except AssemblyStage.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Stage {options["stage"]} not found'))
                return

        # Parse display assignments
        displays = options['displays'].split(',')
        display_1 = '1' in displays
        display_2 = '2' in displays
        display_3 = '3' in displays

        try:
            template, created = BOMTemplate.objects.get_or_create(
                product=product,
                bom_type=options['bom_type'],
                stage=stage,
                defaults={
                    'template_name': options['template_name'],
                    'description': f'BOM template for {options["template_name"]}',
                    'display_screen_1': display_1,
                    'display_screen_2': display_2,
                    'display_screen_3': display_3,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created template: {template.template_name} (ID: {template.id})')
                )
                self.stdout.write(f'   Product: {product.code}')
                self.stdout.write(f'   BOM Type: {template.get_bom_type_display()}')
                self.stdout.write(f'   Stage: {stage.display_name if stage else "None"}')
                self.stdout.write(f'   Displays: {[i+1 for i, x in enumerate([display_1, display_2, display_3]) if x]}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Template already exists: {template.template_name}')
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error creating template: {str(e)}'))

    def list_items(self):
        """List all BOM items"""
        items = BOMItem.objects.all().order_by('item_code')
        
        if not items.exists():
            self.stdout.write(self.style.WARNING('No BOM items found'))
            return

        self.stdout.write('\n📦 BOM Items:')
        self.stdout.write('-' * 100)
        self.stdout.write(f'{"Code":<15} {"Description":<40} {"Part No.":<15} {"Unit":<8} {"Active":<6}')
        self.stdout.write('-' * 100)
        
        for item in items:
            active_status = '✅' if item.is_active else '❌'
            self.stdout.write(
                f'{item.item_code:<15} {item.item_description[:40]:<40} '
                f'{item.part_number:<15} {item.unit_of_measure:<8} {active_status:<6}'
            )
        
        self.stdout.write(f'\nTotal: {items.count()} items')

    def list_templates(self):
        """List all BOM templates"""
        templates = BOMTemplate.objects.all().select_related('product', 'stage')
        
        if not templates.exists():
            self.stdout.write(self.style.WARNING('No BOM templates found'))
            return

        self.stdout.write('\n📋 BOM Templates:')
        self.stdout.write('-' * 120)
        self.stdout.write(f'{"ID":<4} {"Name":<25} {"Product":<12} {"Type":<15} {"Stage":<15} {"Items":<6} {"Displays":<10} {"Active":<6}')
        self.stdout.write('-' * 120)
        
        for template in templates:
            displays = []
            if template.display_screen_1: displays.append('1')
            if template.display_screen_2: displays.append('2')
            if template.display_screen_3: displays.append('3')
            display_str = ','.join(displays) or 'None'
            
            active_status = '✅' if template.is_active else '❌'
            item_count = template.bom_items.filter(is_active=True).count()
            stage_name = template.stage.name if template.stage else 'None'
            
            self.stdout.write(
                f'{template.id:<4} {template.template_name[:25]:<25} {template.product.code:<12} '
                f'{template.bom_type:<15} {stage_name:<15} {item_count:<6} {display_str:<10} {active_status:<6}'
            )
        
        self.stdout.write(f'\nTotal: {templates.count()} templates')

    def preview_bom(self, options):
        """Preview BOM for specific template and quantity"""
        if not options.get('template_id'):
            self.stdout.write(self.style.ERROR('❌ Template ID is required'))
            return

        try:
            template = BOMTemplate.objects.get(id=options['template_id'])
        except BOMTemplate.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Template ID {options["template_id"]} not found'))
            return

        quantity = options['quantity']
        bom_data = template.generate_bom_for_quantity(quantity)
        
        if not bom_data:
            self.stdout.write(self.style.WARNING('No BOM data found'))
            return

        self.stdout.write(f'\n📋 BOM Preview: {template.template_name}')
        self.stdout.write(f'Product: {template.product.code} - {template.product.name}')
        self.stdout.write(f'Quantity: {quantity} units')
        self.stdout.write(f'BOM Type: {template.get_bom_type_display()}')
        if template.stage:
            self.stdout.write(f'Stage: {template.stage.display_name}')
        
        self.stdout.write('\n' + '-' * 100)
        self.stdout.write(f'{"S.NO":<4} {"Description":<40} {"Part No.":<15} {"Quantity":<15} {"Notes":<20}')
        self.stdout.write('-' * 100)
        
        for item_data in bom_data:
            notes = item_data['notes'][:20] if item_data['notes'] else ''
            self.stdout.write(
                f'{item_data["serial_number"]:<4} {item_data["item"].item_description[:40]:<40} '
                f'{item_data["item"].part_number:<15} {item_data["formatted_quantity"]:<15} {notes:<20}'
            )
        
        self.stdout.write(f'\nTotal Items: {len(bom_data)}')

    def bulk_add_items(self, options):
        """Bulk add items from JSON file"""
        if not options.get('json_file'):
            self.stdout.write(self.style.ERROR('❌ JSON file is required'))
            self.stdout.write('\nJSON format example:')
            self.stdout.write('''
[
    {
        "item_code": "ITEM-001",
        "description": "Sample Item",
        "part_number": "P001",
        "unit": "NO.",
        "cost": 10.50,
        "supplier": "ABC Corp"
    }
]
            ''')
            return

        try:
            with open(options['json_file'], 'r') as f:
                items_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ File not found: {options["json_file"]}'))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'❌ Invalid JSON: {str(e)}'))
            return

        if not isinstance(items_data, list):
            self.stdout.write(self.style.ERROR('❌ JSON should contain a list of items'))
            return

        created_count = 0
        updated_count = 0
        error_count = 0

        with transaction.atomic():
            for item_data in items_data:
                try:
                    required_fields = ['item_code', 'description', 'part_number']
                    if not all(field in item_data for field in required_fields):
                        self.stdout.write(
                            self.style.ERROR(f'❌ Missing required fields in: {item_data}')
                        )
                        error_count += 1
                        continue

                    item, created = BOMItem.objects.get_or_create(
                        item_code=item_data['item_code'],
                        defaults={
                            'item_description': item_data['description'],
                            'part_number': item_data['part_number'],
                            'unit_of_measure': item_data.get('unit', 'NO.'),
                            'cost_per_unit': item_data.get('cost'),
                            'supplier': item_data.get('supplier'),
                            'is_active': item_data.get('is_active', True)
                        }
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(f'✅ Created: {item.item_code} - {item.item_description}')
                    else:
                        # Update existing item
                        item.item_description = item_data['description']
                        item.part_number = item_data['part_number']
                        item.unit_of_measure = item_data.get('unit', item.unit_of_measure)
                        if 'cost' in item_data:
                            item.cost_per_unit = item_data['cost']
                        if 'supplier' in item_data:
                            item.supplier = item_data['supplier']
                        if 'is_active' in item_data:
                            item.is_active = item_data['is_active']
                        item.save()
                        updated_count += 1
                        self.stdout.write(f'🔄 Updated: {item.item_code} - {item.item_description}')
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Error processing {item_data}: {str(e)}'))
                    error_count += 1

        self.stdout.write(self.style.SUCCESS(f'\n✅ Bulk operation complete:'))
        self.stdout.write(f'   Created: {created_count} items')
        self.stdout.write(f'   Updated: {updated_count} items')
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'   Errors: {error_count} items'))

# Usage examples in the command help
    def get_help_text(self):
        return """
BOM Helper Command Usage Examples:

1. Add a single item:
   python manage.py bom_helper add_item --item-code="BRG-BOLT-001" --description="M8 Bolt" --part-number="B001" --unit="NO." --cost=0.50

2. Create a template:
   python manage.py bom_helper create_template --template-name="Test BOM" --bom-type="SINGLE_UNIT" --displays="1,2"

3. List all items:
   python manage.py bom_helper list_items

4. List all templates:
   python manage.py bom_helper list_templates

5. Preview BOM:
   python manage.py bom_helper preview_bom --template-id=1 --quantity=50

6. Bulk add from JSON:
   python manage.py bom_helper bulk_add --json-file="items.json"
"""