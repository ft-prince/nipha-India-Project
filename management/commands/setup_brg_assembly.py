# management/commands/setup_brg_assembly.py
from django.core.management.base import BaseCommand
from myapp.models import Product, AssemblyStage, AssemblyProcess, BillOfMaterial, ProductMedia, Station

class Command(BaseCommand):
    help = 'Setup BRG Assembly 40K workflow based on Excel data'

    def handle(self, *args, **options):
        self.stdout.write('Setting up BRG Assembly 40K workflow...')
        
        # 1. Create Product
        product, created = Product.objects.get_or_create(
            code='BRG-40K',
            defaults={'name': 'BRG Assembly 40K'}
        )
        self.stdout.write(f'Product: {product.code} {"created" if created else "exists"}')
        
        # 2. Create Assembly Stages
        stages_data = [
            ('SUB_ASSEMBLY_1', 'BRG Assembly 40K - Sub Assembly 1', 1),
            ('SUB_ASSEMBLY_2', 'BRG Assembly 40K - Sub Assembly 2', 2),
            ('FINAL_ASSEMBLY', 'BRG Assembly 40K - Final Assembly', 3),
        ]
        
        stages = {}
        for stage_code, display_name, order in stages_data:
            stage, created = AssemblyStage.objects.get_or_create(
                name=stage_code,
                defaults={'display_name': display_name, 'order': order}
            )
            stages[stage_code] = stage
            self.stdout.write(f'Stage: {stage.display_name} {"created" if created else "exists"}')
        
        # 3. Create Assembly Processes
        processes_data = [
            # Sub Assembly 1
            ('SUB_ASSEMBLY_1', 'PROCESS 1 OF 3', 'BRG. ASSEMBLY 40K, SUB ASSEMBLY-1 (PROCESS 1 OF 3) OUTSIDE ASSEMBLY ROOM', 'OUTSIDE_ASSEMBLY_ROOM', 1),
            ('SUB_ASSEMBLY_1', 'PROCESS 2 OF 3', 'BRG. ASSEMBLY 40K, SUB ASSEMBLY-1 (PROCESS 2 OF 3) OUTSIDE ASSEMBLY ROOM', 'OUTSIDE_ASSEMBLY_ROOM', 2),
            ('SUB_ASSEMBLY_1', 'PROCESS 3 OF 3', 'BRG. ASSEMBLY 40K, SUB ASSEMBLY-1 (PROCESS 3 OF 3) OUTSIDE ASSEMBLY ROOM', 'OUTSIDE_ASSEMBLY_ROOM', 3),
            
            # Sub Assembly 2
            ('SUB_ASSEMBLY_2', 'PROCESS 1 OF 1', 'BRG. ASSEMBLY 40K, SUB ASSEMBLY-2 (PROCESS 1 OF 1) OUTSIDE ASSEMBLY ROOM', 'OUTSIDE_ASSEMBLY_ROOM', 1),
            
            # Final Assembly
            ('FINAL_ASSEMBLY', 'PROCESS 1A OF 6', 'BRG. ASSEMBLY 40K, FINAL ASSEMBLY (PROCESS 1A OF 6) ASSEMBLY ROOM', 'ASSEMBLY_ROOM', 1),
            ('FINAL_ASSEMBLY', 'PROCESS 1B OF 6', 'BRG. ASSEMBLY 40K, FINAL ASSEMBLY (PROCESS 1B OF 6) ASSEMBLY ROOM', 'ASSEMBLY_ROOM', 2),
            ('FINAL_ASSEMBLY', 'PROCESS 1C OF 6', 'BRG. ASSEMBLY 40K, FINAL ASSEMBLY (PROCESS 1C OF 6) ASSEMBLY ROOM', 'ASSEMBLY_ROOM', 3),
            ('FINAL_ASSEMBLY', 'PROCESS 2 OF 6', 'BRG. ASSEMBLY 40K, FINAL ASSEMBLY (PROCESS 2 OF 6) ASSEMBLY ROOM', 'ASSEMBLY_ROOM', 4),
            ('FINAL_ASSEMBLY', 'PROCESS 3 OF 6', 'BRG. ASSEMBLY 40K, FINAL ASSEMBLY (PROCESS 3 OF 6) OUTSIDE ASSEMBLY ROOM', 'OUTSIDE_ASSEMBLY_ROOM', 5),
            ('FINAL_ASSEMBLY', 'PROCESS 4 OF 6', 'BRG. ASSEMBLY 40K, FINAL ASSEMBLY (PROCESS 4 OF 6) OUTSIDE ASSEMBLY ROOM', 'OUTSIDE_ASSEMBLY_ROOM', 6),
            ('FINAL_ASSEMBLY', 'PROCESS 5 OF 6', 'BRG. ASSEMBLY 40K, FINAL ASSEMBLY (PROCESS 5 OF 6) OUTSIDE ASSEMBLY ROOM', 'OUTSIDE_ASSEMBLY_ROOM', 7),
            ('FINAL_ASSEMBLY', 'PROCESS 6 OF 6', 'BRG. ASSEMBLY 40K, FINAL ASSEMBLY (PROCESS 6 OF 6) OUTSIDE ASSEMBLY ROOM', 'OUTSIDE_ASSEMBLY_ROOM', 8),
        ]
        
        processes = {}
        for stage_code, process_name, display_name, location, order in processes_data:
            stage = stages[stage_code]
            
            # Set loop properties for processes 1A, 1B, 1C
            is_looped = process_name in ['PROCESS 1A OF 6', 'PROCESS 1B OF 6', 'PROCESS 1C OF 6']
            loop_group = 'final_assembly_1abc' if is_looped else None
            
            process, created = AssemblyProcess.objects.get_or_create(
                stage=stage,
                name=process_name,
                defaults={
                    'display_name': display_name,
                    'location': location,
                    'order': order,
                    'is_looped': is_looped,
                    'loop_group': loop_group
                }
            )
            processes[f'{stage_code}_{process_name}'] = process
            self.stdout.write(f'Process: {process.name} {"created" if created else "exists"}')
        
        # 4. Create Bill of Materials
        bom_data = [
            ('SINGLE_UNIT', 'Bill of Material for Single Unit', None),
            ('BATCH_50', 'Bill of Material for 50 Units', None),
            ('SUB_ASSEMBLY_1', 'Bill of Material for Sub Assembly 1', 'SUB_ASSEMBLY_1'),
            ('SUB_ASSEMBLY_2', 'Bill of Material for Sub Assembly 2', 'SUB_ASSEMBLY_2'),
            ('FINAL_ASSEMBLY', 'Bill of Material for Final Assembly', 'FINAL_ASSEMBLY'),
        ]
        
        boms = {}
        for bom_type, description, stage_code in bom_data:
            stage = stages.get(stage_code) if stage_code else None
            bom, created = BillOfMaterial.objects.get_or_create(
                product=product,
                bom_type=bom_type,
                stage=stage,
                defaults={'file': f'bom_files/{bom_type.lower()}.pdf'}  # Placeholder file path
            )
            boms[bom_type] = bom
            self.stdout.write(f'BOM: {bom.get_bom_type_display()} {"created" if created else "exists"}')
        
        # 5. Create Sample Media Files (based on Excel mapping)
        media_data = [
            # Row 1: Single Unit BOM - split among all 3 displays
            ('BOM', 'SINGLE_UNIT', None, True, False, False, 'BILL OF MATERIAL FOR SINGLE UNIT - Display 1'),
            ('BOM', 'SINGLE_UNIT', None, False, True, False, 'BILL OF MATERIAL FOR SINGLE UNIT - Display 2'),
            ('BOM', 'SINGLE_UNIT', None, False, False, True, 'BILL OF MATERIAL FOR SINGLE UNIT - Display 3'),
            
            # Row 2: 50 Units BOM - split among all 3 displays
            ('BOM', 'BATCH_50', None, True, False, False, 'BILL OF MATERIAL FOR 50 UNITS - Display 1'),
            ('BOM', 'BATCH_50', None, False, True, False, 'BILL OF MATERIAL FOR 50 UNITS - Display 2'),
            ('BOM', 'BATCH_50', None, False, False, True, 'BILL OF MATERIAL FOR 50 UNITS - Display 3'),
            
            # Sub Assembly 1 Processes
            ('BOM', 'SUB_ASSEMBLY_1', None, True, False, False, 'SUB ASSEMBLY 1 BOM'),
            ('PROCESS_DOC', None, 'SUB_ASSEMBLY_1_PROCESS 1 OF 3', False, True, False, 'Sub Assembly 1 Process 1 Doc'),
            ('VIDEO', None, 'SUB_ASSEMBLY_1_PROCESS 1 OF 3', False, False, True, 'Sub Assembly 1 Process 1 Video'),
            ('PROCESS_DOC', None, 'SUB_ASSEMBLY_1_PROCESS 2 OF 3', False, True, False, 'Sub Assembly 1 Process 2 Doc'),
            ('VIDEO', None, 'SUB_ASSEMBLY_1_PROCESS 2 OF 3', False, False, True, 'Sub Assembly 1 Process 2 Video'),
            ('PROCESS_DOC', None, 'SUB_ASSEMBLY_1_PROCESS 3 OF 3', False, True, False, 'Sub Assembly 1 Process 3 Doc'),
            ('VIDEO', None, 'SUB_ASSEMBLY_1_PROCESS 3 OF 3', False, False, True, 'Sub Assembly 1 Process 3 Video'),
            
            # Sub Assembly 2 Process
            ('BOM', 'SUB_ASSEMBLY_2', None, True, False, False, 'SUB ASSEMBLY 2 BOM'),
            ('PROCESS_DOC', None, 'SUB_ASSEMBLY_2_PROCESS 1 OF 1', False, True, False, 'Sub Assembly 2 Process Doc'),
            ('VIDEO', None, 'SUB_ASSEMBLY_2_PROCESS 1 OF 1', False, False, True, 'Sub Assembly 2 Process Video'),
            
            # Final Assembly Processes
            ('BOM', 'FINAL_ASSEMBLY', None, True, False, False, 'FINAL ASSEMBLY BOM'),
            ('PROCESS_DOC', None, 'FINAL_ASSEMBLY_PROCESS 1A OF 6', False, True, False, 'Final Assembly Process 1A Doc'),
            ('VIDEO', None, 'FINAL_ASSEMBLY_PROCESS 1A OF 6', False, False, True, 'Final Assembly Process 1A,1B,1C Video'),
            ('PROCESS_DOC', None, 'FINAL_ASSEMBLY_PROCESS 1B OF 6', False, True, False, 'Final Assembly Process 1B Doc'),
            ('PROCESS_DOC', None, 'FINAL_ASSEMBLY_PROCESS 1C OF 6', False, True, False, 'Final Assembly Process 1C Doc'),
            ('PROCESS_DOC', None, 'FINAL_ASSEMBLY_PROCESS 2 OF 6', False, True, False, 'Final Assembly Process 2 Doc'),
            ('VIDEO', None, 'FINAL_ASSEMBLY_PROCESS 2 OF 6', False, False, True, 'Final Assembly Process 2 Video'),
            ('PROCESS_DOC', None, 'FINAL_ASSEMBLY_PROCESS 3 OF 6', False, True, False, 'Final Assembly Process 3 Doc'),
            ('VIDEO', None, 'FINAL_ASSEMBLY_PROCESS 3 OF 6', False, False, True, 'Final Assembly Process 3 Video'),
            ('PROCESS_DOC', None, 'FINAL_ASSEMBLY_PROCESS 4 OF 6', False, True, False, 'Final Assembly Process 4 Doc'),
            ('VIDEO', None, 'FINAL_ASSEMBLY_PROCESS 4 OF 6', False, False, True, 'Final Assembly Process 4 Video'),
            ('PROCESS_DOC', None, 'FINAL_ASSEMBLY_PROCESS 5 OF 6', False, True, False, 'Final Assembly Process 5 Doc'),
            ('VIDEO', None, 'FINAL_ASSEMBLY_PROCESS 5 OF 6', False, False, True, 'Final Assembly Process 5 Video'),
            ('PROCESS_DOC', None, 'FINAL_ASSEMBLY_PROCESS 6 OF 6', False, True, False, 'Final Assembly Process 6 Doc'),
            ('VIDEO', None, 'FINAL_ASSEMBLY_PROCESS 6 OF 6', False, False, True, 'Final Assembly Process 6 Video'),
        ]
        
        for media_type, bom_type, process_key, d1, d2, d3, description in media_data:
            bom = boms.get(bom_type) if bom_type else None
            process = processes.get(process_key) if process_key else None
            
            file_extension = '.mp4' if media_type == 'VIDEO' else '.pdf'
            filename = f"{description.lower().replace(' ', '_')}{file_extension}"
            
            media, created = ProductMedia.objects.get_or_create(
                product=product,
                media_type=media_type,
                process=process,
                bom=bom,
                defaults={
                    'file': f'product_media/{filename}',
                    'display_screen_1': d1,
                    'display_screen_2': d2,
                    'display_screen_3': d3,
                    'duration': 30 if media_type == 'VIDEO' else 15
                }
            )
            if created:
                self.stdout.write(f'Media: {description} - Displays: {[i+1 for i, x in enumerate([d1,d2,d3]) if x]}')
        
        # 6. Create Stations for 3 Displays
        station_data = [
            ('Assembly Station Display 1', 1),
            ('Assembly Station Display 2', 2),
            ('Assembly Station Display 3', 3),
        ]
        
        for station_name, display_num in station_data:
            station, created = Station.objects.get_or_create(
                name=station_name,
                display_number=display_num,
                defaults={
                    'current_product': product,
                    'current_stage': stages['SUB_ASSEMBLY_1'],
                    'current_process': processes['SUB_ASSEMBLY_1_PROCESS 1 OF 3'],
                    'product_quantity': 50,
                    'show_batch_bom': True,
                    'clicker_enabled': True,
                    'loop_mode': False
                }
            )
            station.products.add(product)
            self.stdout.write(f'Station: {station.name} {"created" if created else "exists"}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ BRG Assembly 40K workflow setup complete!'))
        self.stdout.write('\n📋 Summary:')
        self.stdout.write(f'  • Product: {product.code}')
        self.stdout.write(f'  • Stages: {AssemblyStage.objects.count()}')
        self.stdout.write(f'  • Processes: {AssemblyProcess.objects.count()}')
        self.stdout.write(f'  • BOMs: {BillOfMaterial.objects.count()}')
        self.stdout.write(f'  • Media Files: {ProductMedia.objects.count()}')
        self.stdout.write(f'  • Stations: {Station.objects.count()}')
        
        self.stdout.write('\n🎯 Next Steps:')
        self.stdout.write('  1. Upload actual media files to replace placeholders')
        self.stdout.write('  2. Configure stations in Django Admin')
        self.stdout.write('  3. Test clicker functionality')
        self.stdout.write('  4. Set up loop mode for processes 1A, 1B, 1C')
        
        self.stdout.write('\n📝 Usage:')
        self.stdout.write('  • Display 1: Shows BOMs and reference materials')
        self.stdout.write('  • Display 2: Shows process documents and instructions')
        self.stdout.write('  • Display 3: Shows instructional videos')
        self.stdout.write('  • Processes 1A, 1B, 1C will loop until manually advanced to Process 4')
        self.stdout.write('  • Use clicker to navigate forward/backward through processes')
        
        return