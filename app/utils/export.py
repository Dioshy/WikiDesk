import os
import pandas as pd
from datetime import date, datetime, timedelta
from sqlalchemy import func
from app import db
from app.models.entry import Entry
from app.models.user import User
from app.models.courtier import Courtier

class ExcelExporter:
    def __init__(self):
        self.export_dir = 'exports'
        os.makedirs(self.export_dir, exist_ok=True)
    
    def export_daily_report(self, report_date=None):
        """Export daily report for a specific date"""
        if report_date is None:
            report_date = date.today()
        
        # Get entries for the date
        entries = Entry.query.filter(Entry.date == report_date).all()
        
        if not entries:
            raise ValueError(f"No entries found for {report_date}")
        
        # Create filename
        filename = os.path.join(self.export_dir, f'daily_report_{report_date.strftime("%Y%m%d")}.xlsx')
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Summary sheet
            self._create_summary_sheet(entries, writer, f'Daily Report - {report_date}')
            
            # Detailed entries
            self._create_entries_sheet(entries, writer)
            
            # By user summary
            self._create_user_summary_sheet(entries, writer)
            
            # By courtier summary
            self._create_courtier_summary_sheet(entries, writer)
        
        return filename
    
    def export_monthly_report(self, period):
        """Export monthly report for a specific period (YYYYMM)"""
        entries = Entry.query.filter(Entry.period == period).all()
        
        if not entries:
            raise ValueError(f"No entries found for period {period}")
        
        # Create filename
        filename = os.path.join(self.export_dir, f'monthly_report_{period}.xlsx')
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Summary sheet
            self._create_summary_sheet(entries, writer, f'Monthly Report - {period}')
            
            # Daily breakdown
            self._create_daily_breakdown_sheet(entries, writer, period)
            
            # Detailed entries
            self._create_entries_sheet(entries, writer)
            
            # By user summary
            self._create_user_summary_sheet(entries, writer)
            
            # By courtier summary
            self._create_courtier_summary_sheet(entries, writer)
            
            # By type d'acte summary
            self._create_type_dacte_summary_sheet(entries, writer)
        
        return filename
    
    def export_yearly_report(self, year):
        """Export yearly report for a specific year"""
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        entries = Entry.query.filter(
            Entry.date >= start_date,
            Entry.date <= end_date
        ).all()
        
        if not entries:
            raise ValueError(f"No entries found for year {year}")
        
        # Create filename
        filename = os.path.join(self.export_dir, f'yearly_report_{year}.xlsx')
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Summary sheet
            self._create_summary_sheet(entries, writer, f'Yearly Report - {year}')
            
            # Monthly breakdown
            self._create_monthly_breakdown_sheet(entries, writer, year)
            
            # Quarterly breakdown
            self._create_quarterly_breakdown_sheet(entries, writer, year)
            
            # By user summary
            self._create_user_summary_sheet(entries, writer)
            
            # By courtier summary
            self._create_courtier_summary_sheet(entries, writer)
            
            # By type d'acte summary
            self._create_type_dacte_summary_sheet(entries, writer)
            
            # Top clients
            self._create_top_clients_sheet(entries, writer)
        
        return filename
    
    def _create_summary_sheet(self, entries, writer, title):
        """Create summary sheet with key metrics"""
        total_entries = len(entries)
        total_minutes = sum(entry.minutes for entry in entries)
        total_hours = total_minutes / 60
        
        # Get unique users and courtiers
        unique_users = len(set(entry.user_id for entry in entries))
        unique_courtiers = len(set(entry.courtier_id for entry in entries))
        unique_clients = len(set(entry.client_name for entry in entries if entry.client_name))
        
        # Average per entry
        avg_minutes = total_minutes / total_entries if total_entries > 0 else 0
        
        # By type d'acte
        type_breakdown = {}
        for entry in entries:
            type_breakdown[entry.type_dacte] = type_breakdown.get(entry.type_dacte, 0) + entry.minutes
        
        # Create summary data
        summary_data = [
            ['Metric', 'Value'],
            ['Report Title', title],
            ['Generated Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['', ''],
            ['Total Entries', total_entries],
            ['Total Minutes', f'{total_minutes:,}'],
            ['Total Hours', f'{total_hours:.1f}'],
            ['Average Minutes per Entry', f'{avg_minutes:.1f}'],
            ['', ''],
            ['Unique Users', unique_users],
            ['Unique Courtiers', unique_courtiers],
            ['Unique Clients', unique_clients],
            ['', ''],
            ['Breakdown by Type d\'acte', ''],
        ]
        
        for type_dacte, minutes in type_breakdown.items():
            summary_data.append([f'  {type_dacte}', f'{minutes:,} min ({minutes/total_minutes*100:.1f}%)'])
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False, header=False)
        
        # Format the sheet
        worksheet = writer.sheets['Summary']
        worksheet.column_dimensions['A'].width = 25
        worksheet.column_dimensions['B'].width = 20
    
    def _create_entries_sheet(self, entries, writer):
        """Create detailed entries sheet"""
        entries_data = []
        for entry in entries:
            entries_data.append({
                'Date': entry.date.strftime('%Y-%m-%d'),
                'Time': entry.time.strftime('%H:%M:%S'),
                'User': entry.user.full_name,
                'Courtier': entry.courtier.name,
                'Minutes': entry.minutes,
                'Hours': entry.minutes / 60,
                'Type d\'acte': entry.type_dacte,
                'Acte de gestion': entry.acte_de_gestion or '',
                'Dossier': entry.dossier or '',
                'Client Name': entry.client_name or '',
                'Description': entry.description or ''
            })
        
        df_entries = pd.DataFrame(entries_data)
        df_entries.to_excel(writer, sheet_name='Detailed Entries', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Detailed Entries']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    def _create_user_summary_sheet(self, entries, writer):
        """Create user summary sheet"""
        user_stats = {}
        for entry in entries:
            user_id = entry.user_id
            if user_id not in user_stats:
                user_stats[user_id] = {
                    'name': entry.user.full_name,
                    'entries': 0,
                    'minutes': 0,
                    'type_dactes': {}
                }
            
            user_stats[user_id]['entries'] += 1
            user_stats[user_id]['minutes'] += entry.minutes
            
            type_dacte = entry.type_dacte
            if type_dacte not in user_stats[user_id]['type_dactes']:
                user_stats[user_id]['type_dactes'][type_dacte] = 0
            user_stats[user_id]['type_dactes'][type_dacte] += entry.minutes
        
        user_data = []
        for user_id, stats in user_stats.items():
            user_data.append({
                'User': stats['name'],
                'Total Entries': stats['entries'],
                'Total Minutes': stats['minutes'],
                'Total Hours': stats['minutes'] / 60,
                'Avg Minutes/Entry': stats['minutes'] / stats['entries'],
                'Appel téléphonique': stats['type_dactes'].get('Appel téléphonique', 0),
                'Rendez-vous': stats['type_dactes'].get('Rendez-vous', 0),
                'Email': stats['type_dactes'].get('Email', 0),
                'Autre': stats['type_dactes'].get('Autre', 0)
            })
        
        # Sort by total minutes descending
        user_data.sort(key=lambda x: x['Total Minutes'], reverse=True)
        
        df_users = pd.DataFrame(user_data)
        df_users.to_excel(writer, sheet_name='By User', index=False)
    
    def _create_courtier_summary_sheet(self, entries, writer):
        """Create courtier summary sheet"""
        courtier_stats = {}
        for entry in entries:
            courtier_id = entry.courtier_id
            if courtier_id not in courtier_stats:
                courtier_stats[courtier_id] = {
                    'name': entry.courtier.name,
                    'entries': 0,
                    'minutes': 0,
                    'users': set()
                }
            
            courtier_stats[courtier_id]['entries'] += 1
            courtier_stats[courtier_id]['minutes'] += entry.minutes
            courtier_stats[courtier_id]['users'].add(entry.user.full_name)
        
        courtier_data = []
        for courtier_id, stats in courtier_stats.items():
            courtier_data.append({
                'Courtier': stats['name'],
                'Total Entries': stats['entries'],
                'Total Minutes': stats['minutes'],
                'Total Hours': stats['minutes'] / 60,
                'Unique Users': len(stats['users']),
                'Users': ', '.join(stats['users'])
            })
        
        # Sort by total minutes descending
        courtier_data.sort(key=lambda x: x['Total Minutes'], reverse=True)
        
        df_courtiers = pd.DataFrame(courtier_data)
        df_courtiers.to_excel(writer, sheet_name='By Courtier', index=False)
    
    def _create_type_dacte_summary_sheet(self, entries, writer):
        """Create type d'acte summary sheet"""
        type_stats = {}
        for entry in entries:
            type_dacte = entry.type_dacte
            if type_dacte not in type_stats:
                type_stats[type_dacte] = {
                    'entries': 0,
                    'minutes': 0,
                    'users': set(),
                    'courtiers': set()
                }
            
            type_stats[type_dacte]['entries'] += 1
            type_stats[type_dacte]['minutes'] += entry.minutes
            type_stats[type_dacte]['users'].add(entry.user.full_name)
            type_stats[type_dacte]['courtiers'].add(entry.courtier.name)
        
        type_data = []
        for type_dacte, stats in type_stats.items():
            type_data.append({
                'Type d\'acte': type_dacte,
                'Total Entries': stats['entries'],
                'Total Minutes': stats['minutes'],
                'Total Hours': stats['minutes'] / 60,
                'Unique Users': len(stats['users']),
                'Unique Courtiers': len(stats['courtiers'])
            })
        
        df_types = pd.DataFrame(type_data)
        df_types.to_excel(writer, sheet_name='By Type d\'acte', index=False)
    
    def _create_daily_breakdown_sheet(self, entries, writer, period):
        """Create daily breakdown for monthly report"""
        daily_stats = {}
        for entry in entries:
            day_key = entry.date.strftime('%Y-%m-%d')
            if day_key not in daily_stats:
                daily_stats[day_key] = {
                    'date': entry.date,
                    'entries': 0,
                    'minutes': 0
                }
            
            daily_stats[day_key]['entries'] += 1
            daily_stats[day_key]['minutes'] += entry.minutes
        
        daily_data = []
        for day_key, stats in daily_stats.items():
            daily_data.append({
                'Date': stats['date'].strftime('%Y-%m-%d'),
                'Day': stats['date'].strftime('%A'),
                'Entries': stats['entries'],
                'Minutes': stats['minutes'],
                'Hours': stats['minutes'] / 60
            })
        
        # Sort by date
        daily_data.sort(key=lambda x: x['Date'])
        
        df_daily = pd.DataFrame(daily_data)
        df_daily.to_excel(writer, sheet_name='Daily Breakdown', index=False)
    
    def _create_monthly_breakdown_sheet(self, entries, writer, year):
        """Create monthly breakdown for yearly report"""
        monthly_stats = {}
        for entry in entries:
            month_key = entry.date.strftime('%Y-%m')
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'entries': 0,
                    'minutes': 0
                }
            
            monthly_stats[month_key]['entries'] += 1
            monthly_stats[month_key]['minutes'] += entry.minutes
        
        monthly_data = []
        for month_key, stats in monthly_stats.items():
            month_date = datetime.strptime(month_key, '%Y-%m')
            monthly_data.append({
                'Month': month_date.strftime('%B %Y'),
                'Entries': stats['entries'],
                'Minutes': stats['minutes'],
                'Hours': stats['minutes'] / 60
            })
        
        # Sort by month
        monthly_data.sort(key=lambda x: x['Month'])
        
        df_monthly = pd.DataFrame(monthly_data)
        df_monthly.to_excel(writer, sheet_name='Monthly Breakdown', index=False)
    
    def _create_quarterly_breakdown_sheet(self, entries, writer, year):
        """Create quarterly breakdown for yearly report"""
        quarterly_stats = {}
        for entry in entries:
            quarter = (entry.date.month - 1) // 3 + 1
            quarter_key = f'{year} Q{quarter}'
            if quarter_key not in quarterly_stats:
                quarterly_stats[quarter_key] = {
                    'entries': 0,
                    'minutes': 0
                }
            
            quarterly_stats[quarter_key]['entries'] += 1
            quarterly_stats[quarter_key]['minutes'] += entry.minutes
        
        quarterly_data = []
        for quarter_key, stats in quarterly_stats.items():
            quarterly_data.append({
                'Quarter': quarter_key,
                'Entries': stats['entries'],
                'Minutes': stats['minutes'],
                'Hours': stats['minutes'] / 60
            })
        
        df_quarterly = pd.DataFrame(quarterly_data)
        df_quarterly.to_excel(writer, sheet_name='Quarterly Breakdown', index=False)
    
    def _create_top_clients_sheet(self, entries, writer):
        """Create top clients sheet"""
        client_stats = {}
        for entry in entries:
            if not entry.client_name:
                continue
                
            client_name = entry.client_name
            if client_name not in client_stats:
                client_stats[client_name] = {
                    'entries': 0,
                    'minutes': 0,
                    'users': set(),
                    'courtiers': set()
                }
            
            client_stats[client_name]['entries'] += 1
            client_stats[client_name]['minutes'] += entry.minutes
            client_stats[client_name]['users'].add(entry.user.full_name)
            client_stats[client_name]['courtiers'].add(entry.courtier.name)
        
        client_data = []
        for client_name, stats in client_stats.items():
            client_data.append({
                'Client Name': client_name,
                'Total Entries': stats['entries'],
                'Total Minutes': stats['minutes'],
                'Total Hours': stats['minutes'] / 60,
                'Unique Users': len(stats['users']),
                'Unique Courtiers': len(stats['courtiers'])
            })
        
        # Sort by total minutes descending and take top 50
        client_data.sort(key=lambda x: x['Total Minutes'], reverse=True)
        client_data = client_data[:50]
        
        df_clients = pd.DataFrame(client_data)
        df_clients.to_excel(writer, sheet_name='Top Clients', index=False)