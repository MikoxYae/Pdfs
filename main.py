import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path
from PIL import Image, ImageOps
import tempfile
import asyncio

# Bot Token from BotFather
BOT_TOKEN = "8262365802:AAEK1BSrrJtrROFK7tZfxJDRKX_BrFRCQx8"

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_text = """
🤖 **PDF to Black & White Converter Bot**

Send me a PDF file and I'll convert all pages to black and white!

**Features:**
• Converts PDF pages to grayscale
• Maintains original quality
• Fast processing

Just upload your PDF file and wait for the processed version!
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
**How to use this bot:**

1. Send a PDF file to this bot
2. Wait for processing (this may take a moment for large files)
3. Download the converted black and white PDF

**Note:** 
- Maximum file size: 20MB
- Processing time depends on the number of pages
- The bot will preserve the original page dimensions
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

def convert_pdf_to_bw(input_pdf_path, output_pdf_path):
    """Convert PDF pages to black and white."""
    temp_images = []
    try:
        # Read the input PDF
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()
        
        # Convert each page to images and process
        images = convert_from_path(input_pdf_path, dpi=150)
        
        for i, image in enumerate(images):
            # Convert to grayscale
            bw_image = ImageOps.grayscale(image)
            
            # Enhance contrast for better black and white
            bw_image = ImageOps.autocontrast(bw_image, cutoff=2)
            
            # Save temporary image
            temp_img_path = f"temp_page_{i}.png"
            bw_image.save(temp_img_path, "PNG", dpi=(150, 150))
            temp_images.append(temp_img_path)
        
        # Create PDF from processed images
        bw_images = [Image.open(img) for img in temp_images]
        if bw_images:
            bw_images[0].save(
                output_pdf_path,
                "PDF", 
                resolution=150.0,
                save_all=True,
                append_images=bw_images[1:]
            )
        
        # Clean up temporary files
        for temp_img in temp_images:
            if os.path.exists(temp_img):
                os.remove(temp_img)
                
        return True
        
    except Exception as e:
        logger.error(f"Error converting PDF: {e}")
        # Clean up on error
        for temp_img in temp_images:
            if os.path.exists(temp_img):
                os.remove(temp_img)
        return False

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming PDF files."""
    try:
        # Send "processing" message
        processing_msg = await update.message.reply_text("🔄 Processing your PDF... This may take a moment.")
        
        # Get the file
        file = await update.message.document.get_file()
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as input_file:
            input_path = input_file.name
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as output_file:
            output_path = output_file.name
        
        try:
            # Download the PDF file
            await file.download_to_drive(input_path)
            
            # Check file size
            file_size = os.path.getsize(input_path) / (1024 * 1024)  # Size in MB
            if file_size > 20:
                await processing_msg.edit_text("❌ File too large! Please send a PDF smaller than 20MB.")
                return
            
            # Update status
            await processing_msg.edit_text("🎨 Converting pages to black and white...")
            
            # Convert PDF to black and white
            success = convert_pdf_to_bw(input_path, output_path)
            
            if success and os.path.exists(output_path):
                # Check output file size
                output_size = os.path.getsize(output_path)
                if output_size == 0:
                    await processing_msg.edit_text("❌ Error: Output file is empty. Please try again with a different PDF.")
                    return
                
                # Send the converted file
                await processing_msg.edit_text("✅ Conversion complete! Sending your black and white PDF...")
                
                with open(output_path, 'rb') as result_file:
                    await update.message.reply_document(
                        document=result_file,
                        filename="converted_bw.pdf",
                        caption="Here's your PDF converted to black and white! 🎨"
                    )
                
                await processing_msg.delete()
                
            else:
                await processing_msg.edit_text("❌ Failed to convert the PDF. Please make sure it's a valid PDF file and try again.")
                
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            await processing_msg.edit_text("❌ An error occurred while processing your PDF. Please try again.")
            
        finally:
            # Clean up temporary files
            for file_path in [input_path, output_path]:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
    except Exception as e:
        logger.error(f"Error in handle_pdf: {e}")
        await update.message.reply_text("❌ An unexpected error occurred. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and handle them appropriately."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    try:
        await update.message.reply_text("❌ An error occurred. Please try again or contact the bot administrator.")
    except:
        pass

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    application.add_error_handler(error_handler)
    
    # Start the Bot
    print("🤖 Bot is running...")
    print("📞 Bot username: @PDFtoBWConverterBot")
    print("⚡ Ready to receive PDF files!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
