# screen_app/management/commands/update_media_files.py
import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from screen_app.models import ProductMedia, BillOfMaterial

class Command(BaseCommand):
    help = 'Update media files with actual uploaded files'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--source-dir',
            type=str,
            default=r'D:\AI_Model_Renata\phinhaindia\files',
            help='Source directory containing the files'
        )

    def handle(self, *args, **options):
        source_dir = options['source_dir']
        media_root = settings.MEDIA_ROOT
        
        # Ensure media directories exist
        bom_dir = os.path.join(media_root, 'bom_files')
        product_media_dir = os.path.join(media_root, 'product_media')
        
        os.makedirs(bom_dir, exist_ok=True)
        os.makedirs(product_media_dir, exist_ok=True)
        
        self.stdout.write('🚀 Starting media file update...')
        
        # File mapping based on your actual files
        file_mappings = {
            # BOMs
            'BRG. ASSEMBLY 40K - BILL OF MATERIAL (A3 SIZE) - FOR SINGLE UNIT.pdf': {
                'type': 'bom',
                'target': 'single_unit.pdf',
                'bom_type': 'SINGLE_UNIT'
            },
            'BRG. ASSEMBLY 40K - BILL OF MATERIAL (A3 SIZE) - FOR 50 UNITS.pdf': {
                'type': 'bom', 
                'target': 'batch_50.pdf',
                'bom_type': 'BATCH_50'
            },
            'BRG. ASSEMBLY 40K (SUB ASSEMBLY-1) - BILL OF MATERIAL (A3 SIZE) FOR ASSEMBLY ROOM SCREEN 1.pdf': {
                'type': 'bom',
                'target': 'sub_assembly_1.pdf', 
                'bom_type': 'SUB_ASSEMBLY_1'
            },
            'BRG. ASSEMBLY 40K (SUB ASSEMBLY-2) - BILL OF MATERIAL (A3 SIZE) FOR ASSEMBLY ROOM SCREEN 2.pdf': {
                'type': 'bom',
                'target': 'sub_assembly_2.pdf',
                'bom_type': 'SUB_ASSEMBLY_2'
            },
            'BRG. ASSEMBLY 40K (FINAL ASSEMBLY) - BILL OF MATERIAL (A3 SIZE) FOR ASSEMBLY ROOM SCREEN 3.pdf': {
                'type': 'bom',
                'target': 'final_assembly.pdf',
                'bom_type': 'FINAL_ASSEMBLY'
            },
            
            # Process Videos
            '01 - BRG. ASSEMBLY 40K, SUB ASSEMBLY-1 (PROCESS 1 OF 3) OUTSIDE ASSEMBLY ROOM.mp4': {
                'type': 'video',
                'target': 'sub_assembly_1_process_1_video.mp4',
                'stage': 'SUB_ASSEMBLY_1',
                'process': 'PROCESS 1 OF 3'
            },
            '02 - BRG. ASSEMBLY 40K, SUB ASSEMBLY-1 (PROCESS 2 OF 3) OUTSIDE ASSEMBLY ROOM.mp4': {
                'type': 'video',
                'target': 'sub_assembly_1_process_2_video.mp4',
                'stage': 'SUB_ASSEMBLY_1', 
                'process': 'PROCESS 2 OF 3'
            },
            '03 - BRG. ASSEMBLY 40K, SUB ASSEMBLY-1 (PROCESS 3 OF 3) OUTSIDE ASSEMBLY ROOM.mp4': {
                'type': 'video',
                'target': 'sub_assembly_1_process_3_video.mp4',
                'stage': 'SUB_ASSEMBLY_1',
                'process': 'PROCESS 3 OF 3'
            },
            '04 - BRG. ASSEMBLY 40K, SUB ASSEMBLY-2 (PROCESS 1 OF 1) OUTSIDE ASSEMBLY ROOM.mp4': {
                'type': 'video',
                'target': 'sub_assembly_2_process_video.mp4',
                'stage': 'SUB_ASSEMBLY_2',
                'process': 'PROCESS 1 OF 1'
            },
            '05 - BRG. ASSEMBLY 40K (PROCESS 1 OF 6) INSIDE ASSEMBLY ROOM.mp4': {
                'type': 'video',
                'target': 'final_assembly_process_1a,1b,1c_video.mp4',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 1A OF 6'  # This will be used for 1A, 1B, 1C
            },
            '06 - BRG. ASSEMBLY 40K (PROCESS 2 OF 6) INSIDE ASSEMBLY ROOM.mp4': {
                'type': 'video',
                'target': 'final_assembly_process_2_video.mp4',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 2 OF 6'
            },
            '07 - BRG. ASSEMBLY 40K (PROCESS 3 OF 6) OUTSIDE ASSEMBLY ROOM.mp4': {
                'type': 'video',
                'target': 'final_assembly_process_3_video.mp4',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 3 OF 6'
            },
            '08 - BRG. ASSEMBLY 40K (PROCESS 4 OF 6) OUTSIDE ASSEMBLY ROOM.mp4': {
                'type': 'video',
                'target': 'final_assembly_process_4_video.mp4',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 4 OF 6'
            },
            '09 - BRG. ASSEMBLY 40K (PROCESS 5 OF 6) OUTSIDE ASSEMBLY ROOM.mp4': {
                'type': 'video',
                'target': 'final_assembly_process_5_video.mp4',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 5 OF 6'
            },
            '10 - BRG. ASSEMBLY 40K (PROCESS 6 OF 6) OUTSIDE ASSEMBLY ROOM.mp4': {
                'type': 'video',
                'target': 'final_assembly_process_6_video.mp4',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 6 OF 6'
            },
            
            # Process Documents
            '1 PROCESS SEQUENCE - 40K (NOT IN ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'sub_assembly_1_process_1_doc.pdf',
                'stage': 'SUB_ASSEMBLY_1',
                'process': 'PROCESS 1 OF 3'
            },
            '2 PROCESS SEQUENCE - 40K (NOT IN ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'sub_assembly_1_process_2_doc.pdf',
                'stage': 'SUB_ASSEMBLY_1',
                'process': 'PROCESS 2 OF 3'
            },
            '3 PROCESS SEQUENCE - 40K (NOT IN ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'sub_assembly_1_process_3_doc.pdf',
                'stage': 'SUB_ASSEMBLY_1',
                'process': 'PROCESS 3 OF 3'
            },
            '4 PROCESS SEQUENCE - 40K (NOT IN ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'sub_assembly_2_process_doc.pdf',
                'stage': 'SUB_ASSEMBLY_2',
                'process': 'PROCESS 1 OF 1'
            },
            '5 PROCESS SEQUENCE - 40K (STEP 1 INSIDE ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'final_assembly_process_1a_doc.pdf',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 1A OF 6'
            },
            '6 PROCESS SEQUENCE - 40K (STEP 2 INSIDE ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'final_assembly_process_1b_doc.pdf',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 1B OF 6'
            },
            '7 PROCESS SEQUENCE - 40K (STEP 3 INSIDE ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'final_assembly_process_1c_doc.pdf',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 1C OF 6'
            },
            '8 PROCESS SEQUENCE - 40K (STEP 4 INSIDE ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'final_assembly_process_2_doc.pdf',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 2 OF 6'
            },
            '9 PROCESS SEQUENCE - 40K (NOT IN ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'final_assembly_process_3_doc.pdf',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 3 OF 6'
            },
            '10 PROCESS SEQUENCE - 40K (NOT IN ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'final_assembly_process_4_doc.pdf',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 4 OF 6'
            },
            '11 PROCESS SEQUENCE - 40K (NOT IN ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'final_assembly_process_5_doc.pdf',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 5 OF 6'
            },
            '12 PROCESS SEQUENCE - 40K (NOT IN ASSEMBLY ROOM).pdf': {
                'type': 'doc',
                'target': 'final_assembly_process_6_doc.pdf',
                'stage': 'FINAL_ASSEMBLY',
                'process': 'PROCESS 6 OF 6'
            }
        }
        
        copied_files = 0
        updated_records = 0
        
        # Process each file mapping
        for source_file, mapping in file_mappings.items():
            source_path = os.path.join(source_dir, source_file)
            
            if not os.path.exists(source_path):
                self.stdout.write(f'⚠️  File not found: {source_file}')
                continue
            
            # Determine target directory and path
            if mapping['type'] == 'bom':
                target_dir = bom_dir
                target_path = os.path.join(target_dir, mapping['target'])
                relative_path = f"bom_files/{mapping['target']}"
            else:
                target_dir = product_media_dir
                target_path = os.path.join(target_dir, mapping['target'])
                relative_path = f"product_media/{mapping['target']}"
            
            # Copy file
            try:
                shutil.copy2(source_path, target_path)
                self.stdout.write(f'✅ Copied: {source_file} → {mapping["target"]}')
                copied_files += 1
                
                # Update database records
                if mapping['type'] == 'bom':
                    # Update BillOfMaterial
                    try:
                        bom = BillOfMaterial.objects.get(bom_type=mapping['bom_type'])
                        bom.file = relative_path
                        bom.save()
                        self.stdout.write(f'📋 Updated BOM: {mapping["bom_type"]}')
                        updated_records += 1
                    except BillOfMaterial.DoesNotExist:
                        self.stdout.write(f'⚠️  BOM not found: {mapping["bom_type"]}')
                
                else:
                    # Update ProductMedia
                    try:
                        # Find the media record by process and type
                        from screen_app.models import AssemblyStage, AssemblyProcess
                        
                        stage = AssemblyStage.objects.get(name=mapping['stage'])
                        process = AssemblyProcess.objects.get(stage=stage, name=mapping['process'])
                        
                        if mapping['type'] == 'video':
                            media_type = 'VIDEO'
                        else:
                            media_type = 'PROCESS_DOC'
                        
                        media = ProductMedia.objects.get(
                            process=process,
                            media_type=media_type
                        )
                        media.file = relative_path
                        media.save()
                        
                        # For process 1A video, also update 1B and 1C to use the same file
                        if mapping['process'] == 'PROCESS 1A OF 6' and mapping['type'] == 'video':
                            for proc_name in ['PROCESS 1B OF 6', 'PROCESS 1C OF 6']:
                                try:
                                    proc = AssemblyProcess.objects.get(stage=stage, name=proc_name)
                                    proc_media = ProductMedia.objects.get(process=proc, media_type='VIDEO')
                                    proc_media.file = relative_path
                                    proc_media.save()
                                    self.stdout.write(f'🔗 Linked {proc_name} to same video')
                                except:
                                    pass
                        
                        self.stdout.write(f'📱 Updated Media: {mapping["stage"]} - {mapping["process"]}')
                        updated_records += 1
                        
                    except Exception as e:
                        self.stdout.write(f'⚠️  Media update failed: {mapping["stage"]} - {mapping["process"]} - {str(e)}')
                
            except Exception as e:
                self.stdout.write(f'❌ Copy failed: {source_file} - {str(e)}')
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n🎉 File update complete!'))
        self.stdout.write(f'📁 Files copied: {copied_files}')
        self.stdout.write(f'💾 Database records updated: {updated_records}')
        self.stdout.write(f'\n📺 Your displays are now ready with actual content!')
        self.stdout.write(f'🔗 Test your displays:')
        self.stdout.write(f'   • Display 1: http://127.0.0.1:8000/station/1/slider/')
        self.stdout.write(f'   • Display 2: http://127.0.0.1:8000/station/2/slider/')
        self.stdout.write(f'   • Display 3: http://127.0.0.1:8000/station/3/slider/')
        
        return