#!/usr/bin/env python3
"""
EMAIL HANDLER - Real-time and scheduled email notifications
"""

import smtplib
import sqlite3
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
import logging

logger = logging.getLogger(__name__)


class EmailHandler:
    """Handle real-time and scheduled email notifications"""
    
    def __init__(self, config):
        self.config = config
        self.scheduler = BackgroundScheduler()
        self.db_file = 'agent_database.db'
        
    def send_realtime_confirmation(self, image_file, records_count, sheet_name):
        """Send real-time confirmation email after processing"""
        if not self.config.get('email_enabled'):
            return False
        
        try:
            subject = f"✓ Delivery Report Processed - {sheet_name}"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px;">
                        <h2 style="color: #27ae60;">✓ Delivery Report Successfully Processed</h2>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                            <p><strong>Processing Details:</strong></p>
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr style="background-color: #ecf0f1;">
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Date</strong></td>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;">{sheet_name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Image File</strong></td>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;">{image_file}</td>
                                </tr>
                                <tr style="background-color: #ecf0f1;">
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Records Processed</strong></td>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>{records_count}</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Status</strong></td>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><span style="color: #27ae60; font-weight: bold;">SUCCESS</span></td>
                                </tr>
                                <tr style="background-color: #ecf0f1;">
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Time</strong></td>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                                </tr>
                            </table>
                        </div>
                        
                        <p style="color: #7f8c8d; font-size: 12px;">
                            <strong>Note:</strong> Delivery report has been automatically processed and saved to your Excel master file.
                            A new sheet named "{sheet_name}" has been created with all delivery records.
                        </p>
                        
                        <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #bdc3c7; color: #7f8c8d; font-size: 11px;">
                            <p>Autonomous Delivery Report Agent | Safetech Precast Manufacturing</p>
                            <p>This is an automated message. Do not reply directly to this email.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            return self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"Error sending real-time email: {str(e)}")
            return False
    
    def send_daily_summary(self):
        """Send daily summary report at scheduled time"""
        if not self.config.get('email_enabled'):
            return False
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            stats = self._get_daily_stats(today)
            
            subject = f"📊 Daily Delivery Report Summary - {today}"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px;">
                        <h2 style="color: #3498db;">📊 Daily Delivery Report Summary</h2>
                        <p style="font-size: 14px; color: #555;">Report Date: <strong>{today}</strong></p>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 20px 0;">
                            <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db;">
                                <p style="margin: 0; font-size: 12px; color: #555;">Total Reports Processed</p>
                                <p style="margin: 0; font-size: 28px; font-weight: bold; color: #3498db;">{stats['total_reports']}</p>
                            </div>
                            
                            <div style="background-color: #e8f8f1; padding: 15px; border-radius: 5px; border-left: 4px solid #27ae60;">
                                <p style="margin: 0; font-size: 12px; color: #555;">Total Delivery Records</p>
                                <p style="margin: 0; font-size: 28px; font-weight: bold; color: #27ae60;">{stats['total_records']}</p>
                            </div>
                        </div>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                            <h3 style="margin-top: 0; color: #333;">Processing Details</h3>
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr style="background-color: #ecf0f1;">
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Metric</strong></td>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Value</strong></td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;">Reports Successfully Processed</td>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><span style="color: #27ae60; font-weight: bold;">{stats['total_reports']}</span></td>
                                </tr>
                                <tr style="background-color: #ecf0f1;">
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;">Total Delivery Records</td>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;"><span style="color: #3498db; font-weight: bold;">{stats['total_records']}</span></td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;">Average Records per Report</td>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;">
                                        {round(stats['total_records'] / max(stats['total_reports'], 1), 1)}
                                    </td>
                                </tr>
                                <tr style="background-color: #ecf0f1;">
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;">Report Generated</td>
                                    <td style="padding: 8px; border: 1px solid #bdc3c7;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                                </tr>
                            </table>
                        </div>
                        
                        <div style="background-color: #fffbea; padding: 12px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #f39c12;">
                            <p style="margin: 0; font-size: 12px; color: #555;">
                                ℹ️ <strong>Note:</strong> All delivery reports have been automatically processed and saved to your Excel master file.
                                New sheets have been created for each date with all delivery records and lookups.
                            </p>
                        </div>
                        
                        <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #bdc3c7; color: #7f8c8d; font-size: 11px;">
                            <p>Autonomous Delivery Report Agent | Daily Summary Report</p>
                            <p>This is an automated message. Do not reply directly to this email.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            return self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {str(e)}")
            return False
    
    def _send_email(self, subject, body):
        """Internal method to send email via SMTP"""
        try:
            # Determine SMTP server based on email type
            email_address = self.config.get('email_address', '')
            
            if 'gmail.com' in email_address:
                smtp_server = 'smtp.gmail.com'
                smtp_port = 587
            elif 'outlook.com' in email_address or 'hotmail.com' in email_address:
                smtp_server = 'smtp-mail.outlook.com'
                smtp_port = 587
            else:
                smtp_server = self.config.get('smtp_server', 'smtp.gmail.com')
                smtp_port = self.config.get('smtp_port', 587)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = email_address
            msg['To'] = ', '.join(self.config.get('email_recipients', []))
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_address, self.config.get('email_password', ''))
                server.send_message(msg)
            
            logger.info(f"Email sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"SMTP Error: {str(e)}")
            return False
    
    def _get_daily_stats(self, date):
        """Get statistics for a specific date"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as total_reports, SUM(records_count) as total_records
                FROM processed_reports
                WHERE DATE(timestamp) = ? AND status = 'SUCCESS'
            ''', (date,))
            
            result = cursor.fetchone()
            conn.close()
            
            return {
                'total_reports': result[0] or 0,
                'total_records': result[1] or 0
            }
        except Exception as e:
            logger.error(f"Error getting daily stats: {str(e)}")
            return {'total_reports': 0, 'total_records': 0}
    
    def schedule_daily_summary(self, time_str='08:10'):
        """Schedule daily summary email at specific time"""
        try:
            hour, minute = map(int, time_str.split(':'))
            
            self.scheduler.add_job(
                self.send_daily_summary,
                'cron',
                hour=hour,
                minute=minute,
                id='daily_summary'
            )
            
            if not self.scheduler.running:
                self.scheduler.start()
            
            logger.info(f"Daily summary scheduled for {time_str}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling daily summary: {str(e)}")
            return False
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
