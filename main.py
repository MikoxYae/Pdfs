import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path
from PIL import Image, ImageOps, ImageChops
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

# Conversation states
WAITING_FOR_PDF = 1

# Store user choices
user_choices = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_text = """
🤖 **PDF Converter Bot**

**Available Commands:**

/start - Show this welcome message
/help - Get help and instructions
/bw - Convert PDF to Black & White
/invert - Invert PDF colors (Negative/Reverse)

**Features:**
• Convert PDF to grayscale
• Invert colors (black to white, white to black)
• Maintains original quality
• Fast processing

Choose a command and send your PDF!
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
**How to use this bot:**

**For Black & White Conversion:**
1. Send `/bw` command
2. Upload your PDF file
3. Wait for processing
4. Download the converted PDF

**For Color Inversion:**
1. Send `/invert` command  
2. Upload your PDF file
3. Wait for processing
4. Download the inverted PDF

**Note:** 
- Maximum file size: 20MB
- Processing time depends on the number of pages
- The bot will preserve the original page dimensions
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def bw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bw command - ask for PDF."""
    user_id = update.effective_user.id
    user_choices[user_id] = 'bw'
    
    await update.message.reply_text(
        "🎨 **Black & White Conversion**\n\n"
        "Please upload your PDF file and I'll convert it to black and white!",
        parse_mode='Markdown'
    )
    
    return WAITING_FOR_PDF

async def invert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /invert command - ask for PDF."""
    user_id = update.effective_user.id
    user_choices[user_id] = 'invert'
    
    await update.message.reply_text(
        "🔄 **Color Inversion**\n\n"
        "Please upload your PDF file and I'll invert all colors "
        "(black becomes white, white becomes black, etc.)",
        parse_mode='Markdown'
    )
    
    return WAITING_FOR_PDF

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    user_id = update.effective_user.id
    if user_id in user_choices:
        del user_choices[user_id]
    
    await update.message.reply_text(
        "❌ Operation cancelled.",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

def convert_pdf_to_bw(input_pdf_path, output_pdf_path):
    """Convert PDF pages to black and white."""
    temp_images = []
    try:
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
        logger.error(f"Error converting PDF to BW: {e}")
        # Clean up on error
        for temp_img in temp_images:
            if os.path.exists(temp_img):
                os.remove(temp_img)
        return False

def convert_pdf_to_invert(input_pdf_path, output_pdf_path):
    """Convert PDF pages to inverted colors."""
    temp_images = []
    try:
        # Convert each page to images and process
        images = convert_from_path(input_pdf_path, dpi=150)
        
        for i, image in enumerate(images):
            # Convert to RGB if needed
            if image.mode == 'P':
                image = image.convert('RGB')
            elif image.mode == 'LA':
                image = image.convert('L')
            
            # Invert colors
            if image.mode == 'RGB':
                # For color images, invert each channel
                inverted_image = ImageChops.invert(image)
            else:
                # For grayscale images
                inverted_image = ImageOps.invert(image)
            
            # Save temporary image
            temp_img_path = f"temp_page_{i}.png"
            inverted_image.save(temp_img_path, "PNG", dpi=(150, 150))
            temp_images.append(temp_img_path)
        
        # Create PDF from processed images
        inverted_images = [Image.open(img) for img in temp_images]
        if inverted_images:
            inverted_images[0].save(
                output_pdf_path,
                "PDF", 
                resolution=150.0,
                save_all=True,
                append_images=inverted_images[1:]
            )
        
        # Clean up temporary files
        for temp_img in temp_images:
            if os.path.exists(temp_img):
                os.remove(temp_img)
                
        return True
        
    except Exception as e:
        logger.error(f"Error inverting PDF colors: {e}")
        # Clean up on error
        for temp_img in temp_images:
            if os.path.exists(temp_img):
                os.remove(temp_img)
        return False

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming PDF files based on user choice."""
    user_id = update.effective_user.id
    
    # Check if user has chosen an operation
    if user_id not in user_choices:
        await update.message.reply_text(
            "❌ Please choose an operation first using /bw or /invert command.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    operation = user_choices[user_id]
    operation_name = "Black & White" if operation == 'bw' else "Color Inversion"
    
    try:
        # Send "processing" message
        processing_msg = await update.message.reply_text(f"🔄 Processing your PDF for {operation_name}... This may take a moment.")
        
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
                return ConversationHandler.END
            
            # Update status
            await processing_msg.edit_text(f"🎨 Converting pages - {operation_name}...")
            
            # Convert PDF based on operation
            if operation == 'bw':
                success = convert_pdf_to_bw(input_path, output_path)
                caption = "Here's your PDF converted to black and white! 🎨"
                filename = "converted_bw.pdf"
            else:  # invert
                success = convert_pdf_to_invert(input_path, output_path)
                caption = "Here's your PDF with inverted colors! 🔄"
                filename = "inverted_colors.pdf"
            
            if success and os.path.exists(output_path):
                # Check output file size
                output_size = os.path.getsize(output_path)
                if output_size == 0:
                    await processing_msg.edit_text("❌ Error: Output file is empty. Please try again with a different PDF.")
                    return ConversationHandler.END
                
                # Send the converted file
                await processing_msg.edit_text("✅ Conversion complete! Sending your PDF...")
                
                with open(output_path, 'rb') as result_file:
                    await update.message.reply_document(
                        document=result_file,
                        filename=filename,
                        caption=caption
                    )
                
                await processing_msg.delete()
                
            else:
                await processing_msg.edit_text("❌ Failed to process the PDF. Please make sure it's a valid PDF file and try again.")
                
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            await processing_msg.edit_text("❌ An error occurred while processing your PDF. Please try again.")
            
        finally:
            # Clean up temporary files and user choice
            if user_id in user_choices:
                del user_choices[user_id]
            for file_path in [input_path, output_path]:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
    except Exception as e:
        logger.error(f"Error in handle_pdf: {e}")
        await update.message.reply_text("❌ An unexpected error occurred. Please try again.")
        if user_id in user_choices:
            del user_choices[user_id]
    
    return ConversationHandler.END

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
    
    # Create conversation handler for /bw and /invert commands
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('bw', bw_command),
            CommandHandler('invert', invert_command)
        ],
        states={
            WAITING_FOR_PDF: [
                MessageHandler(filters.Document.PDF, handle_pdf)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    
    # Start the Bot
    print("🤖 Bot is running...")
    print("📞 Bot username: @PDFConverterBot")
    print("⚡ Available commands: /bw, /invert")
    print("📚 Ready to receive PDF files!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
