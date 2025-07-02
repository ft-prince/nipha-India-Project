# management/commands/setup_bom_items.py
from django.core.management.base import BaseCommand
from screen_app.models import BOMItem, BOMTemplate, BOMTemplateItem, Product, AssemblyStage

class Command(BaseCommand):
    help = 'Setup BOM items from your documents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all BOM data before setup',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting BOM data...')
            BOMTemplateItem.objects.all().delete()
            BOMTemplate.objects.all().delete()
            BOMItem.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ BOM data reset complete'))

        self.stdout.write('Setting up BOM items from your documents...')
        
        # Create BOM Items based on your documents
        bom_items_data = [
            # From Single Unit BOM document
            {
                'item_code': 'BRG-NUT-001',
                'description': 'NUT',
                'part_number': '04172923',
                'unit': 'NO.',
                'notes': 'Standard nut for BRG assembly'
            },
            {
                'item_code': 'BRG-HUB-001', 
                'description': 'HUB',
                'part_number': '04172929',
                'unit': 'NO.',
                'notes': 'Main hub component'
            },
            {
                'item_code': 'BRG-PIN-001',
                'description': '5/8" DIA X 3 3/8" LONG ALUMINIUM PIN',
                'part_number': '01210254',
                'unit': 'NO.',
                'notes': 'Precision aluminium pin'
            },
            {
                'item_code': 'BRG-COTTER-001',
                'description': '3/16" X 4" SS COTTER PIN',
                'part_number': 'B.O.',
                'unit': 'NO.',
                'notes': 'Stainless steel cotter pin - bought out item'
            },
            {
                'item_code': 'BRG-SHAFT-001',
                'description': 'SHAFT',
                'part_number': '01518001',
                'unit': 'NO.',
                'notes': 'Primary shaft component'
            },
            {
                'item_code': 'BRG-INNER-001',
                'description': 'INNER BEARING RACE',
                'part_number': '01380013',
                'unit': 'NO.',
                'notes': 'Inner bearing race - 2 pieces per assembly'
            },
            {
                'item_code': 'BRG-BALL-001',
                'description': 'BALL ½"',
                'part_number': 'B.O.',
                'unit': 'NO.',
                'notes': 'Ball bearing - 46 pieces per assembly'
            },
            {
                'item_code': 'BRG-OUTER-001',
                'description': 'OUTER BEARING RACE',
                'part_number': '01380012',
                'unit': 'NO.',
                'notes': 'Outer bearing race - 2 pieces per assembly'
            },
            {
                'item_code': 'BRG-HOUSING-001',
                'description': 'HOUSING',
                'part_number': '04172930',
                'unit': 'NO.',
                'notes': 'Main housing component'
            },
            {
                'item_code': 'BRG-SEAL-001',
                'description': 'BEARING SEAL',
                'part_number': 'B.O.',
                'unit': 'NO.',
                'notes': 'Bearing seal - 2 pieces per assembly'
            },
            {
                'item_code': 'BRG-LOCTITE-001',
                'description': 'LOCKTITE LB 8008 C5-A',
                'part_number': 'B.O.',
                'unit': 'GM',
                'notes': 'Thread locking compound'
            },
            # Sub-assemblies for Final Assembly
            {
                'item_code': 'BRG-SUB1-001',
                'description': 'SUB ASSEMBLY 01',
                'part_number': '--',
                'unit': 'NO.',
                'notes': 'Completed sub assembly 1'
            },
            {
                'item_code': 'BRG-SUB2-001',
                'description': 'SUB ASSEMBLY 02',
                'part_number': '--',
                'unit': 'NO.',
                'notes': 'Completed sub assembly 2 - ensure outer race is pressed on both sides'
            },
        ]

        created_items = {}
        for item_data in bom_items_data:
            item, created = BOMItem.objects.get_or_create(
                item_code=item_data['item_code'],
                defaults={
                    'item_description': item_data['description'],
                    'part_number': item_data['part_number'],
                    'unit_of_measure': item_data['unit'],
                    'is_active': True
                }
            )
            created_items[item_data['item_code']] = item
            status = "created" if created else "exists"
            self.stdout.write(f'  • {item.item_code}: {item.item_description} ({status})')

        # Get or create product
        product, _ = Product.objects.get_or_create(
            code='BRG-40K',
            defaults={'name': 'BRG Assembly 40K'}
        )

        # Get stages
        stages = {
            'SUB_ASSEMBLY_1': AssemblyStage.objects.get(name='SUB_ASSEMBLY_1'),
            'SUB_ASSEMBLY_2': AssemblyStage.objects.get(name='SUB_ASSEMBLY_2'),
            'FINAL_ASSEMBLY': AssemblyStage.objects.get(name='FINAL_ASSEMBLY'),
        }

        self.stdout.write('\nCreating BOM Templates...')

        # BOM Templates data based on your documents
        bom_templates_data = [
            {
                'name': 'Single Unit BOM',
                'bom_type': 'SINGLE_UNIT',
                'stage': None,
                'displays': [True, True, True],  # Show on all displays
                'items': [
                    ('BRG-NUT-001', 1, 1),
                    ('BRG-HUB-001', 2, 1),
                    ('BRG-PIN-001', 3, 1),
                    ('BRG-COTTER-001', 4, 1),
                    ('BRG-SHAFT-001', 5, 1),
                    ('BRG-INNER-001', 6, 2),
                    ('BRG-BALL-001', 7, 46),
                    ('BRG-OUTER-001', 8, 2),
                    ('BRG-HOUSING-001', 10, 1),
                    ('BRG-SEAL-001', 11, 2),
                    ('BRG-LOCTITE-001', 12, 0.005),  # 0.005 KGS for single unit
                ]
            },
            {
                'name': '50 Units BOM',
                'bom_type': 'BATCH_50',
                'stage': None,
                'displays': [True, True, True],  # Show on all displays
                'items': [
                    ('BRG-NUT-001', 1, 1),
                    ('BRG-HUB-001', 2, 1),
                    ('BRG-PIN-001', 3, 1),
                    ('BRG-COTTER-001', 4, 1),
                    ('BRG-SHAFT-001', 5, 1),
                    ('BRG-INNER-001', 6, 2),
                    ('BRG-BALL-001', 7, 46),
                    ('BRG-OUTER-001', 8, 2),
                    ('BRG-HOUSING-001', 10, 1),
                    ('BRG-SEAL-001', 11, 2),
                    ('BRG-LOCTITE-001', 12, 0.02),  # 1GM for 50 units = 0.02 per unit
                ]
            },
            {
                'name': 'Sub Assembly 1 BOM',
                'bom_type': 'SUB_ASSEMBLY_1',
                'stage': 'SUB_ASSEMBLY_1',
                'displays': [True, False, False],  # Show on display 1 only
                'items': [
                    ('BRG-HUB-001', 1, 1),
                    ('BRG-PIN-001', 2, 1),
                    ('BRG-SHAFT-001', 3, 1),
                ]
            },
            {
                'name': 'Sub Assembly 2 BOM',
                'bom_type': 'SUB_ASSEMBLY_2', 
                'stage': 'SUB_ASSEMBLY_2',
                'displays': [True, False, False],  # Show on display 1 only
                'items': [
                    ('BRG-OUTER-001', 1, 2),
                    ('BRG-HOUSING-001', 2, 1),
                ]
            },
            {
                'name': 'Final Assembly BOM',
                'bom_type': 'FINAL_ASSEMBLY',
                'stage': 'FINAL_ASSEMBLY',
                'displays': [True, False, False],  # Show on display 1 only
                'items': [
                    ('BRG-SUB1-001', 1, 1),
                    ('BRG-SUB2-001', 2, 1),
                    ('BRG-NUT-001', 3, 1),
                    ('BRG-COTTER-001', 4, 1),
                    ('BRG-INNER-001', 5, 2),
                    ('BRG-BALL-001', 6, 46),
                    ('BRG-SEAL-001', 7, 2),
                    ('BRG-LOCTITE-001', 8, 0.02),  # 1GM total
                ]
            },
        ]

        for template_data in bom_templates_data:
            # Create BOM Template
            stage = stages.get(template_data['stage']) if template_data['stage'] else None
            
            template, created = BOMTemplate.objects.get_or_create(
                product=product,
                bom_type=template_data['bom_type'],
                stage=stage,
                defaults={
                    'template_name': template_data['name'],
                    'description': f"Database BOM for {template_data['name']}",
                    'display_screen_1': template_data['displays'][0],
                    'display_screen_2': template_data['displays'][1],
                    'display_screen_3': template_data['displays'][2],
                    'is_active': True
                }
            )
            
            status = "created" if created else "exists"
            self.stdout.write(f'  📋 {template.template_name} ({status})')
            
            # Add items to template
            if created:
                for item_code, serial_no, quantity in template_data['items']:
                    item = created_items[item_code]
                    BOMTemplateItem.objects.create(
                        bom_template=template,
                        item=item,
                        base_quantity=quantity,
                        serial_number=serial_no,
                        is_active=True
                    )
                    self.stdout.write(f'    • {serial_no:02d}. {item.item_description} - {quantity} {item.unit_of_measure}')

        self.stdout.write(self.style.SUCCESS('\n✅ BOM setup complete!'))
        self.stdout.write('\n📊 Summary:')
        self.stdout.write(f'  • BOM Items: {BOMItem.objects.count()}')
        self.stdout.write(f'  • BOM Templates: {BOMTemplate.objects.count()}')
        self.stdout.write(f'  • Template Items: {BOMTemplateItem.objects.count()}')
        
        self.stdout.write('\n🎯 Next Steps:')
        self.stdout.write('  1. Upload item photos in Django Admin (BOM Items)')
        self.stdout.write('  2. Set cost and supplier information')
        self.stdout.write('  3. Test BOM generation with different quantities')
        self.stdout.write('  4. Configure station BOM display settings')
        
        self.stdout.write('\n📝 Usage Examples:')
        self.stdout.write('  • Single unit: Shows exact quantities for 1 piece')
        self.stdout.write('  • 50 units batch: Multiplies quantities by 50')
        self.stdout.write('  • Sub assemblies: Shows only required components per stage')
        self.stdout.write('  • Final assembly: Uses completed sub-assemblies')
        
        return