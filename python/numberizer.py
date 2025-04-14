from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def get_page_size(page):
    """Extract the actual page size from a PDF page"""
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    return width, height

def create_page_number_overlay(page_num, page_width, page_height, alignment, font_name, font_size, 
                              prefix="", suffix="", margin_bottom=30, text_color=(0, 0, 0)):
    """Create a PDF overlay with page number"""
    packet = io.BytesIO()
    
    # Use actual page dimensions
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))
    
    # Set text color (RGB values between 0 and 1)
    r, g, b = text_color
    c.setFillColorRGB(r/255, g/255, b/255)
    
    # Set font
    c.setFont(font_name, font_size)
    
    # Create page number text with optional prefix/suffix
    page_text = f"{prefix}{page_num}{suffix}"
    text_width = pdfmetrics.stringWidth(page_text, font_name, font_size)
    
    # Calculate position based on alignment
    if alignment == 'left':
        x_pos = 50
    elif alignment == 'center':
        x_pos = page_width / 2 - text_width / 2
    elif alignment == 'right':
        x_pos = page_width - 50 - text_width
    
    # Draw the text
    c.drawString(x_pos, margin_bottom, page_text)
    c.save()
    
    # Move to beginning of buffer
    packet.seek(0)
    return packet

def process_page(args):
    """Process a single page (for parallel processing)"""
    page, page_num, start_page, alignment, font_name, font_size, prefix, suffix, margin_bottom, text_color = args
    
    # Get actual page dimensions
    page_width, page_height = get_page_size(page)
    
    # Create page number overlay
    packet = create_page_number_overlay(
        page_num + start_page, 
        page_width, 
        page_height, 
        alignment, 
        font_name, 
        font_size, 
        prefix, 
        suffix, 
        margin_bottom,
        text_color
    )
    
    # Create PDF from buffer
    number_pdf = PdfReader(packet)
    number_page = number_pdf.pages[0]
    
    # Merge original page with overlay
    page.merge_page(number_page)
    
    return page_num, page

def add_page_numbers(input_pdf, output_pdf, alignment='center', start_page=1, 
                    font='Helvetica', font_size=12, prefix="", suffix="", 
                    margin_bottom=30, text_color=(0, 0, 0), page_range=None,
                    max_workers=None):
    """
    Add page numbers to a PDF document.
    
    Args:
        input_pdf (str): Path to input PDF file
        output_pdf (str): Path to output PDF file
        alignment (str): Page number alignment ('left', 'center', 'right')
        start_page (int): Starting page number
        font (str): Font for page numbers
        font_size (int): Font size for page numbers
        prefix (str): Text to appear before page number
        suffix (str): Text to appear after page number
        margin_bottom (int): Bottom margin in points
        text_color (tuple): RGB color tuple (0-255, 0-255, 0-255)
        page_range (tuple): Optional (start, end) tuple for page range to process
        max_workers (int): Maximum number of worker threads (None = auto)
    """
    start_time = time.time()
    
    # Validate alignment
    valid_alignments = ['left', 'center', 'right']
    if alignment.lower() not in valid_alignments:
        raise ValueError(f"Alignment must be one of: {valid_alignments}")
    
    # Read input PDF
    logger.info(f"Reading PDF: {input_pdf}")
    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    
    # Determine page range
    total_pages = len(reader.pages)
    if page_range:
        start_idx, end_idx = page_range
        # Adjust for zero-based indexing
        start_idx = max(0, start_idx - 1)
        end_idx = min(total_pages, end_idx)
        pages_to_process = range(start_idx, end_idx)
    else:
        pages_to_process = range(total_pages)
    
    # Create a list of arguments for each page
    page_args = [
        (reader.pages[i], i, start_page, alignment, font, font_size, 
         prefix, suffix, margin_bottom, text_color) 
        for i in pages_to_process
    ]
    
    processed_pages = {}
    
    # Process pages using ThreadPoolExecutor for parallel processing
    logger.info(f"Processing {len(pages_to_process)} pages...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_page, args): args for args in page_args}
        
        for future in as_completed(futures):
            try:
                page_num, page = future.result()
                processed_pages[page_num] = page
            except Exception as e:
                logger.error(f"Error processing page: {e}")
    
    # Add pages to writer (maintaining original order)
    for i in range(total_pages):
        if i in processed_pages:
            writer.add_page(processed_pages[i])
        else:
            # For pages not in the specified range
            writer.add_page(reader.pages[i])
    
    # Save the output PDF
    logger.info(f"Writing output to: {output_pdf}")
    with open(output_pdf, 'wb') as output_file:
        writer.write(output_file)
    
    # Log completion
    elapsed_time = time.time() - start_time
    logger.info(f"Completed in {elapsed_time:.2f} seconds")
    
    return output_pdf

def register_custom_font(font_path, font_name):
    """Register a custom TrueType font for use in PDF"""
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        return True
    return False

def parse_page_range(page_range_str):
    """Parse page range string like '1-5' into a tuple (1, 5)"""
    if not page_range_str:
        return None
    
    try:
        if '-' in page_range_str:
            start, end = page_range_str.split('-')
            return (int(start), int(end))
        else:
            # Single page
            page = int(page_range_str)
            return (page, page)
    except ValueError:
        raise ValueError("Page range must be in format '1-5' or a single number")

def parse_color(color_str):
    """Parse color string like '255,0,0' into RGB tuple"""
    if not color_str:
        return (0, 0, 0)  # Default black
    
    try:
        r, g, b = map(int, color_str.split(','))
        return (r, g, b)
    except ValueError:
        raise ValueError("Color must be in format 'R,G,B' with values 0-255")

def main():
    """Main function with command-line interface"""
    # Create argument parser
    parser = argparse.ArgumentParser(
        description='Add page numbers to PDF documents',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Add arguments
    parser.add_argument('input_pdf', help='Input PDF file path')
    parser.add_argument('-o', '--output', help='Output PDF file path')
    parser.add_argument('-a', '--alignment', choices=['left', 'center', 'right'], 
                        default='center', help='Page number alignment')
    parser.add_argument('-s', '--start', type=int, default=1, 
                        help='Starting page number')
    parser.add_argument('-f', '--font', default='Helvetica', 
                        help='Font name for page numbers')
    parser.add_argument('--font-path', help='Path to custom TTF font file')
    parser.add_argument('--font-size', type=int, default=12, 
                        help='Font size for page numbers')
    parser.add_argument('--prefix', default='', help='Text to appear before page number')
    parser.add_argument('--suffix', default='', help='Text to appear after page number')
    parser.add_argument('--margin-bottom', type=int, default=30, 
                        help='Bottom margin in points')
    parser.add_argument('--color', default='0,0,0', 
                        help='Text color in RGB format (e.g., 255,0,0 for red)')
    parser.add_argument('--page-range', help='Page range to process (e.g., 1-5)')
    parser.add_argument('--threads', type=int, help='Number of worker threads')
    
    # Parse arguments
    if len(os.sys.argv) > 1:
        args = parser.parse_args()
        interactive_mode = False
    else:
        # If no arguments provided, use interactive mode
        args = parser.parse_args(['dummy'])  # Temporary argument to avoid error
        interactive_mode = True
    
    try:
        if interactive_mode:
            # Interactive mode
            print("=== PDF Page Numberer ===")
            
            # Get input file
            input_pdf = input("Enter input PDF path: ")
            if not os.path.exists(input_pdf):
                raise FileNotFoundError(f"Input file not found: {input_pdf}")
            
            # Get output file
            default_output = os.path.splitext(input_pdf)[0] + "_numbered.pdf"
            output_pdf = input(f"Enter output PDF path (default: {default_output}): ") or default_output
            
            # Get alignment
            alignment = input("Choose alignment (left/center/right) [center]: ").lower() or "center"
            if alignment not in ['left', 'center', 'right']:
                alignment = 'center'
            
            # Get start page
            try:
                start_page = int(input("Enter starting page number [1]: ") or 1)
            except ValueError:
                start_page = 1
            
            # Get font size
            try:
                font_size = int(input("Enter font size [12]: ") or 12)
            except ValueError:
                font_size = 12
            
            # Get font
            font = input("Enter font name [Helvetica]: ") or "Helvetica"
            
            # Get custom font path (optional)
            font_path = input("Enter custom font path (optional): ")
            if font_path and os.path.exists(font_path):
                register_custom_font(font_path, font)
            
            # Get prefix/suffix
            prefix = input("Enter prefix text (optional): ")
            suffix = input("Enter suffix text (optional): ")
            
            # Get margin
            try:
                margin_bottom = int(input("Enter bottom margin [30]: ") or 30)
            except ValueError:
                margin_bottom = 30
            
            # Get color
            color_str = input("Enter text color (R,G,B) [0,0,0]: ") or "0,0,0"
            try:
                text_color = parse_color(color_str)
            except ValueError:
                print("Invalid color format. Using default black.")
                text_color = (0, 0, 0)
            
            # Get page range
            page_range_str = input("Enter page range (e.g., 1-5, optional): ")
            page_range = parse_page_range(page_range_str) if page_range_str else None
            
            # Get thread count
            try:
                threads = int(input("Enter number of threads (optional, leave blank for auto): ") or 0)
                if threads <= 0:
                    threads = None
            except ValueError:
                threads = None
            
        else:
            # Command-line mode
            input_pdf = args.input_pdf
            if not os.path.exists(input_pdf):
                raise FileNotFoundError(f"Input file not found: {input_pdf}")
            
            # Generate default output filename if not specified
            if args.output:
                output_pdf = args.output
            else:
                output_pdf = os.path.splitext(input_pdf)[0] + "_numbered.pdf"
            
            alignment = args.alignment
            start_page = args.start
            font = args.font
            font_size = args.font_size
            prefix = args.prefix
            suffix = args.suffix
            margin_bottom = args.margin_bottom
            text_color = parse_color(args.color)
            page_range = parse_page_range(args.page_range) if args.page_range else None
            threads = args.threads
            
            # Register custom font if provided
            if args.font_path:
                if register_custom_font(args.font_path, args.font):
                    logger.info(f"Registered custom font: {args.font}")
                else:
                    logger.warning(f"Custom font not found: {args.font_path}")
        
        # Call the main function to add page numbers
        add_page_numbers(
            input_pdf, 
            output_pdf, 
            alignment, 
            start_page, 
            font, 
            font_size,
            prefix,
            suffix,
            margin_bottom,
            text_color,
            page_range,
            threads
        )
        
        print(f"\nSuccess! PDF with page numbers saved as: {output_pdf}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print(f"\nError: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
