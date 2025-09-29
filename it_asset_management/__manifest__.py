{
    'name': 'IT Asset Management',
    'version': '1.0',
    'category': 'Operations',
    'summary': 'Manage IT Assets, Requests and Assignments',
    'description': """
        IT Asset Management Module
        ===========================
        This module helps manage:
        - IT Assets inventory
        - Asset assignments to employees
        - Asset requests
        - Asset categories
    """,
    'author': 'Your Company',
    'depends': ['base', 'mail', 'portal', 'hr'],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data files
        'data/sequences.xml',
        'data/asset_categories.xml',
        'data/email_templates.xml',
        'data/admin_access.xml',
        'data/users_demo.xml',
        'data/sample_assets.xml',
        'data/extended_assets.xml',
        'data/sample_assignments.xml',
        'data/extended_requests.xml',
        'data/extended_assignments.xml',
        
        # Views
        'views/asset_views.xml',
        'views/asset_request_views.xml',
        'views/assignment_views.xml',
        'views/dashboard_views.xml',
        'views/config_settings_views.xml',
        # 'views/wizard_views.xml',  # Temporarily disabled
        'views/portal_templates.xml',
        
        # Menus (must be last)
        'views/menus.xml',
    ],
    # 'demo': [
    #     'data/demo_assets.xml',
    # ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
