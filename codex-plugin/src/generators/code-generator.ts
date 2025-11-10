import fs from 'fs-extra';
import path from 'path';

export class CodeGenerator {
  private templates = {
    react: {
      component: this.getReactComponentTemplate(),
      hook: this.getReactHookTemplate(),
      context: this.getReactContextTemplate(),
      redux: this.getReduxTemplate()
    },
    vue: {
      component: this.getVueComponentTemplate(),
      store: this.getVueStoreTemplate(),
      composable: this.getVueComposableTemplate()
    },
    node: {
      express: this.getExpressTemplate(),
      api: this.getApiTemplate(),
      middleware: this.getMiddlewareTemplate(),
      model: this.getModelTemplate()
    },
    python: {
      django_model: this.getDjangoModelTemplate(),
      flask_api: this.getFlaskApiTemplate(),
      class: this.getPythonClassTemplate(),
      test: this.getPythonTestTemplate()
    },
    odoo: {
      module: this.getOdooModuleTemplate(),
      model: this.getOdooModelTemplate(),
      view: this.getOdooViewTemplate(),
      controller: this.getOdooControllerTemplate(),
      security: this.getOdooSecurityTemplate()
    }
  };

  async generateBoilerplate(
    type: string,
    name: string,
    options: any = {},
    outputPath?: string
  ): Promise<string> {
    const [framework, template] = type.split('-');

    let code = '';

    if (framework === 'react') {
      code = this.generateReactBoilerplate(template, name, options);
    } else if (framework === 'vue') {
      code = this.generateVueBoilerplate(template, name, options);
    } else if (framework === 'node' || framework === 'express') {
      code = this.generateNodeBoilerplate(template, name, options);
    } else if (framework === 'django' || framework === 'flask') {
      code = this.generatePythonBoilerplate(framework, template, name, options);
    } else if (framework === 'odoo') {
      code = await this.generateOdooBoilerplate(template, name, options);
    } else {
      code = this.generateGenericBoilerplate(type, name, options);
    }

    if (outputPath) {
      await fs.ensureDir(path.dirname(outputPath));
      await fs.writeFile(outputPath, code);
      return `Generated ${type} boilerplate at ${outputPath}`;
    }

    return code;
  }

  async generateTests(
    sourcePath: string,
    framework: string = 'jest',
    coverage: string = 'comprehensive'
  ): Promise<string> {
    const content = await fs.readFile(sourcePath, 'utf-8');
    const language = this.detectLanguage(sourcePath);

    if (language === 'javascript' || language === 'typescript') {
      return this.generateJavaScriptTests(content, framework, coverage);
    } else if (language === 'python') {
      return this.generatePythonTests(content, framework, coverage);
    } else if (language === 'java') {
      return this.generateJavaTests(content, coverage);
    }

    return '// Test generation not supported for this file type';
  }

  async generateDocumentation(
    targetPath: string,
    format: string,
    includeExamples: boolean = true
  ): Promise<string> {
    const content = await fs.readFile(targetPath, 'utf-8');
    const language = this.detectLanguage(targetPath);

    switch (format) {
      case 'jsdoc':
        return this.generateJSDoc(content, includeExamples);
      case 'docstring':
        return this.generateDocstrings(content, includeExamples);
      case 'markdown':
        return this.generateMarkdownDocs(content, language, includeExamples);
      case 'openapi':
        return this.generateOpenApiDocs(content, includeExamples);
      default:
        return '// Documentation format not supported';
    }
  }

  async convertCode(
    source: string,
    from: string,
    to: string,
    preserveComments: boolean = true
  ): Promise<string> {
    // Check if source is a file path
    let content = source;
    if (await fs.pathExists(source)) {
      content = await fs.readFile(source, 'utf-8');
    }

    // Common conversions
    if (from === 'javascript' && to === 'typescript') {
      return this.convertJsToTs(content, preserveComments);
    } else if (from === 'class' && to === 'hooks') {
      return this.convertClassToHooks(content);
    } else if (from === 'callbacks' && to === 'promises') {
      return this.convertCallbacksToPromises(content);
    } else if (from === 'promises' && to === 'async') {
      return this.convertPromisesToAsync(content);
    } else if (from === 'commonjs' && to === 'esm') {
      return this.convertCommonJsToEsm(content);
    }

    return `// Conversion from ${from} to ${to} not yet implemented`;
  }

  async createProjectStructure(
    stack: string,
    projectName: string,
    features: string[] = [],
    outputPath?: string
  ): Promise<string> {
    const projectPath = outputPath || path.join(process.cwd(), projectName);
    const structure = this.getProjectStructure(stack, features);

    // Create directories
    for (const dir of structure.directories) {
      await fs.ensureDir(path.join(projectPath, dir));
    }

    // Create files
    for (const [filePath, content] of Object.entries(structure.files)) {
      const fullPath = path.join(projectPath, filePath);
      await fs.ensureDir(path.dirname(fullPath));
      await fs.writeFile(fullPath, content as string);
    }

    return `Created ${stack} project structure at ${projectPath}\n\nStructure:\n${structure.directories.join('\n')}`;
  }

  async createOdooModule(
    moduleName: string,
    version: string,
    features: string[] = [],
    projectPath?: string
  ): Promise<string> {
    const modulePath = projectPath || path.join(process.cwd(), moduleName);

    const structure = {
      directories: [
        'models',
        'views',
        'security',
        'data',
        'controllers',
        'static/src/js',
        'static/src/scss',
        'static/src/xml',
        'reports',
        'wizard',
        'tests'
      ],
      files: {
        '__manifest__.py': this.getOdooManifest(moduleName, version, features),
        '__init__.py': this.getOdooInit(features),
        'models/__init__.py': '# -*- coding: utf-8 -*-\n',
        'controllers/__init__.py': '# -*- coding: utf-8 -*-\n',
        'security/ir.model.access.csv': this.getOdooAccessCsv(moduleName)
      }
    };

    // Add feature-specific files
    if (features.includes('model')) {
      structure.files[`models/${moduleName}.py`] = this.getOdooModelTemplate()
        .replace('MODULE_NAME', moduleName)
        .replace('ModelName', this.toPascalCase(moduleName));
    }

    if (features.includes('views')) {
      structure.files[`views/${moduleName}_views.xml`] = this.getOdooViewTemplate()
        .replace(/MODULE_NAME/g, moduleName);
    }

    if (features.includes('controller')) {
      structure.files[`controllers/main.py`] = this.getOdooControllerTemplate()
        .replace('MODULE_NAME', moduleName);
    }

    if (features.includes('security')) {
      structure.files['security/security.xml'] = this.getOdooSecurityGroupsTemplate(moduleName);
    }

    // Create the module structure
    for (const dir of structure.directories) {
      await fs.ensureDir(path.join(modulePath, dir));
    }

    for (const [filePath, content] of Object.entries(structure.files)) {
      const fullPath = path.join(modulePath, filePath);
      await fs.ensureDir(path.dirname(fullPath));
      await fs.writeFile(fullPath, content);
    }

    return `Created Odoo ${version} module "${moduleName}" at ${modulePath}`;
  }

  async generateOdooSecurity(
    modulePath: string,
    models: string[],
    groups: string[] = []
  ): Promise<string> {
    const accessCsv = this.generateOdooAccessCsv(models, groups);
    const securityXml = this.generateOdooSecurityXml(models, groups);

    // Write files
    const csvPath = path.join(modulePath, 'security', 'ir.model.access.csv');
    const xmlPath = path.join(modulePath, 'security', 'security.xml');

    await fs.ensureDir(path.dirname(csvPath));
    await fs.writeFile(csvPath, accessCsv);
    await fs.writeFile(xmlPath, securityXml);

    return `Generated security files:\n- ${csvPath}\n- ${xmlPath}\n\nCSV:\n${accessCsv}\n\nXML:\n${securityXml}`;
  }

  // Template methods
  private getReactComponentTemplate(): string {
    return `import React, { useState, useEffect } from 'react';
import './COMPONENT_NAME.css';

interface COMPONENT_NAMEProps {
  // Add props here
}

const COMPONENT_NAME: React.FC<COMPONENT_NAMEProps> = (props) => {
  const [state, setState] = useState(null);

  useEffect(() => {
    // Component did mount
    return () => {
      // Cleanup
    };
  }, []);

  return (
    <div className="COMPONENT_NAME">
      <h1>COMPONENT_NAME Component</h1>
      {/* Add your component content here */}
    </div>
  );
};

export default COMPONENT_NAME;`;
  }

  private getReactHookTemplate(): string {
    return `import { useState, useEffect, useCallback } from 'react';

interface UseHOOK_NAMEOptions {
  // Add options here
}

interface UseHOOK_NAMEResult {
  // Add return type here
  data: any;
  loading: boolean;
  error: Error | null;
}

export const useHOOK_NAME = (options?: UseHOOK_NAMEOptions): UseHOOK_NAMEResult => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Add your logic here
      setData(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error };
};`;
  }

  private getReactContextTemplate(): string {
    return `import React, { createContext, useContext, useState, ReactNode } from 'react';

interface CONTEXT_NAMEType {
  // Add context type here
  value: any;
  setValue: (value: any) => void;
}

const CONTEXT_NAMEContext = createContext<CONTEXT_NAMEType | undefined>(undefined);

export const CONTEXT_NAMEProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [value, setValue] = useState(null);

  return (
    <CONTEXT_NAMEContext.Provider value={{ value, setValue }}>
      {children}
    </CONTEXT_NAMEContext.Provider>
  );
};

export const useCONTEXT_NAME = () => {
  const context = useContext(CONTEXT_NAMEContext);
  if (!context) {
    throw new Error('useCONTEXT_NAME must be used within CONTEXT_NAMEProvider');
  }
  return context;
};`;
  }

  private getReduxTemplate(): string {
    return `import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface SLICE_NAMEState {
  // Add state type here
  data: any[];
  loading: boolean;
  error: string | null;
}

const initialState: SLICE_NAMEState = {
  data: [],
  loading: false,
  error: null,
};

const SLICE_NAMESlice = createSlice({
  name: 'SLICE_NAME',
  initialState,
  reducers: {
    fetchStart: (state) => {
      state.loading = true;
      state.error = null;
    },
    fetchSuccess: (state, action: PayloadAction<any[]>) => {
      state.loading = false;
      state.data = action.payload;
    },
    fetchError: (state, action: PayloadAction<string>) => {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const { fetchStart, fetchSuccess, fetchError } = SLICE_NAMESlice.actions;
export default SLICE_NAMESlice.reducer;`;
  }

  private getVueComponentTemplate(): string {
    return `<template>
  <div class="COMPONENT_NAME">
    <h1>{{ title }}</h1>
    <!-- Add your template here -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

// Props
interface Props {
  // Add props here
}
const props = defineProps<Props>();

// State
const title = ref('COMPONENT_NAME');

// Computed
const computedValue = computed(() => {
  // Add computed logic here
  return title.value;
});

// Methods
const handleClick = () => {
  // Add method logic here
};

// Lifecycle
onMounted(() => {
  // Component mounted
});
</script>

<style scoped>
.COMPONENT_NAME {
  /* Add styles here */
}
</style>`;
  }

  private getVueStoreTemplate(): string {
    return `import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useSTORE_NAMEStore = defineStore('STORE_NAME', () => {
  // State
  const items = ref<any[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Getters
  const itemCount = computed(() => items.value.length);

  // Actions
  async function fetchItems() {
    loading.value = true;
    error.value = null;
    try {
      // Add fetch logic here
      items.value = [];
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  }

  function addItem(item: any) {
    items.value.push(item);
  }

  function removeItem(id: string) {
    const index = items.value.findIndex(item => item.id === id);
    if (index > -1) {
      items.value.splice(index, 1);
    }
  }

  return {
    // State
    items,
    loading,
    error,
    // Getters
    itemCount,
    // Actions
    fetchItems,
    addItem,
    removeItem
  };
});`;
  }

  private getVueComposableTemplate(): string {
    return `import { ref, computed, watch, Ref } from 'vue';

interface UseCOMPOSABLE_NAMEOptions {
  // Add options here
}

export function useCOMPOSABLE_NAME(options?: UseCOMPOSABLE_NAMEOptions) {
  // State
  const data = ref<any>(null);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  // Computed
  const hasData = computed(() => data.value !== null);

  // Methods
  const fetchData = async () => {
    loading.value = true;
    error.value = null;
    try {
      // Add fetch logic here
      data.value = null;
    } catch (err) {
      error.value = err as Error;
    } finally {
      loading.value = false;
    }
  };

  // Watchers
  watch(data, (newValue) => {
    // React to data changes
  });

  return {
    data,
    loading,
    error,
    hasData,
    fetchData
  };
}`;
  }

  private getExpressTemplate(): string {
    return `import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(morgan('dev'));

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'API is running' });
});

app.get('/api/items', async (req, res) => {
  try {
    // Add your logic here
    res.json({ items: [] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/items', async (req, res) => {
  try {
    const { body } = req;
    // Add your logic here
    res.status(201).json({ item: body });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// Start server
app.listen(PORT, () => {
  console.log(\`Server is running on port \${PORT}\`);
});

export default app;`;
  }

  private getApiTemplate(): string {
    return `import { Router } from 'express';

const router = Router();

// Get all items
router.get('/', async (req, res) => {
  try {
    // Add your logic here
    res.json({ items: [] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get single item
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    // Add your logic here
    res.json({ item: { id } });
  } catch (error) {
    res.status(404).json({ error: 'Item not found' });
  }
});

// Create item
router.post('/', async (req, res) => {
  try {
    const { body } = req;
    // Add validation and creation logic here
    res.status(201).json({ item: body });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Update item
router.put('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { body } = req;
    // Add update logic here
    res.json({ item: { id, ...body } });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Delete item
router.delete('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    // Add deletion logic here
    res.status(204).send();
  } catch (error) {
    res.status(404).json({ error: 'Item not found' });
  }
});

export default router;`;
  }

  private getMiddlewareTemplate(): string {
    return `import { Request, Response, NextFunction } from 'express';

export const MIDDLEWARE_NAME = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    // Add middleware logic here

    // Example: Authentication check
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    // Validate token and set user
    // req.user = await validateToken(token);

    next();
  } catch (error) {
    res.status(403).json({ error: 'Invalid token' });
  }
};`;
  }

  private getModelTemplate(): string {
    return `import mongoose, { Document, Schema } from 'mongoose';

export interface IMODEL_NAME extends Document {
  name: string;
  description?: string;
  createdAt: Date;
  updatedAt: Date;
  // Add more fields here
}

const MODEL_NAMESchema = new Schema<IMODEL_NAME>(
  {
    name: {
      type: String,
      required: true,
      trim: true,
    },
    description: {
      type: String,
      trim: true,
    },
    // Add more fields here
  },
  {
    timestamps: true,
  }
);

// Add indexes
MODEL_NAMESchema.index({ name: 1 });

// Add methods
MODEL_NAMESchema.methods.toJSON = function() {
  const obj = this.toObject();
  delete obj.__v;
  return obj;
};

// Add statics
MODEL_NAMESchema.statics.findByName = function(name: string) {
  return this.findOne({ name });
};

export default mongoose.model<IMODEL_NAME>('MODEL_NAME', MODEL_NAMESchema);`;
  }

  private getDjangoModelTemplate(): string {
    return `from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class MODEL_NAME(models.Model):
    """
    MODEL_NAME model description
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_MODEL_NAMES')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'MODEL_NAME'
        ordering = ['-created_at']
        verbose_name = 'MODEL_NAME'
        verbose_name_plural = 'MODEL_NAMEs'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Add custom save logic here
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return f"{self.name} - {self.created_at.strftime('%Y-%m-%d')}"`;
  }

  private getFlaskApiTemplate(): string {
    return `from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

# Model
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }

# Routes
@app.route('/api/items', methods=['GET'])
def get_items():
    items = Item.query.all()
    return jsonify([item.to_dict() for item in items])

@app.route('/api/items/<int:id>', methods=['GET'])
def get_item(id):
    item = Item.query.get_or_404(id)
    return jsonify(item.to_dict())

@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.get_json()
    item = Item(
        name=data['name'],
        description=data.get('description', '')
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201

@app.route('/api/items/<int:id>', methods=['PUT'])
def update_item(id):
    item = Item.query.get_or_404(id)
    data = request.get_json()
    item.name = data.get('name', item.name)
    item.description = data.get('description', item.description)
    db.session.commit()
    return jsonify(item.to_dict())

@app.route('/api/items/<int:id>', methods=['DELETE'])
def delete_item(id):
    item = Item.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return '', 204

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)`;
  }

  private getPythonClassTemplate(): string {
    return `from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CLASS_NAME:
    """
    CLASS_NAME description
    """

    def __init__(self, name: str, **kwargs):
        """
        Initialize CLASS_NAME

        Args:
            name: The name of the instance
            **kwargs: Additional keyword arguments
        """
        self.name = name
        self.created_at = datetime.now()
        self._data: Dict[str, Any] = {}

        # Process additional arguments
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        return f"CLASS_NAME(name={self.name})"

    def __repr__(self) -> str:
        return f"CLASS_NAME(name={self.name}, created_at={self.created_at})"

    @property
    def age(self) -> float:
        """Calculate age in seconds"""
        return (datetime.now() - self.created_at).total_seconds()

    def process(self, data: Any) -> Any:
        """
        Process data

        Args:
            data: Input data to process

        Returns:
            Processed data
        """
        logger.info(f"Processing data for {self.name}")
        # Add processing logic here
        self._data['last_processed'] = datetime.now()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CLASS_NAME':
        """Create instance from dictionary"""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to dictionary"""
        return {
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'data': self._data
        }`;
  }

  private getPythonTestTemplate(): string {
    return `import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest

class TestCLASS_NAME(unittest.TestCase):
    """Test suite for CLASS_NAME"""

    def setUp(self):
        """Set up test fixtures"""
        self.instance = CLASS_NAME("test")

    def tearDown(self):
        """Tear down test fixtures"""
        pass

    def test_initialization(self):
        """Test CLASS_NAME initialization"""
        self.assertEqual(self.instance.name, "test")
        self.assertIsNotNone(self.instance.created_at)

    def test_string_representation(self):
        """Test string representation"""
        self.assertEqual(str(self.instance), "CLASS_NAME(name=test)")

    def test_process_method(self):
        """Test process method"""
        data = {"key": "value"}
        result = self.instance.process(data)
        self.assertEqual(result, data)

    @patch('module.dependency')
    def test_with_mock(self, mock_dependency):
        """Test with mocked dependency"""
        mock_dependency.return_value = "mocked"
        # Add test logic here
        pass

    def test_edge_case(self):
        """Test edge cases"""
        with self.assertRaises(ValueError):
            # Add edge case test
            pass

# Pytest style tests
class TestCLASS_NAMEPytest:
    """Pytest style test suite"""

    @pytest.fixture
    def instance(self):
        """Create instance fixture"""
        return CLASS_NAME("test")

    def test_basic_functionality(self, instance):
        """Test basic functionality"""
        assert instance.name == "test"

    @pytest.mark.parametrize("input,expected", [
        ("test1", "test1"),
        ("test2", "test2"),
    ])
    def test_parametrized(self, input, expected):
        """Test with parameters"""
        instance = CLASS_NAME(input)
        assert instance.name == expected

if __name__ == '__main__':
    unittest.main()`;
  }

  private getOdooModuleTemplate(): string {
    return `# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ModelName(models.Model):
    _name = 'MODULE_NAME.model'
    _description = 'MODULE_NAME Model'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        help='Enter the name'
    )

    description = fields.Text(
        string='Description',
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade'
    )

    amount = fields.Float(
        string='Amount',
        digits='Product Price',
        compute='_compute_amount',
        store=True
    )

    date = fields.Date(
        string='Date',
        default=fields.Date.today,
        required=True
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.depends('partner_id')
    def _compute_amount(self):
        for record in self:
            # Add computation logic here
            record.amount = 0.0

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(_('Amount cannot be negative!'))

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id:
            # Add onchange logic here
            pass

    def action_confirm(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft records can be confirmed.'))
        self.state = 'confirmed'

    def action_done(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Only confirmed records can be marked as done.'))
        self.state = 'done'

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.model
    def create(self, vals):
        # Add custom create logic here
        return super(ModelName, self).create(vals)

    def write(self, vals):
        # Add custom write logic here
        return super(ModelName, self).write(vals)`;
  }

  private getOdooModelTemplate(): string {
    return this.getOdooModuleTemplate();
  }

  private getOdooViewTemplate(): string {
    return `<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Tree View -->
    <record id="MODULE_NAME_tree_view" model="ir.ui.view">
        <field name="name">MODULE_NAME.tree</field>
        <field name="model">MODULE_NAME.model</field>
        <field name="arch" type="xml">
            <tree string="MODULE_NAME">
                <field name="name"/>
                <field name="partner_id"/>
                <field name="date"/>
                <field name="amount" sum="Total Amount"/>
                <field name="state" widget="badge" decoration-success="state == 'done'" decoration-warning="state == 'confirmed'" decoration-info="state == 'draft'"/>
            </tree>
        </field>
    </record>

    <!-- Form View -->
    <record id="MODULE_NAME_form_view" model="ir.ui.view">
        <field name="name">MODULE_NAME.form</field>
        <field name="model">MODULE_NAME.model</field>
        <field name="arch" type="xml">
            <form string="MODULE_NAME">
                <header>
                    <button name="action_confirm" type="object" string="Confirm" class="btn-primary" attrs="{'invisible': [('state', '!=', 'draft')]}"/>
                    <button name="action_done" type="object" string="Mark as Done" class="btn-success" attrs="{'invisible': [('state', '!=', 'confirmed')]}"/>
                    <button name="action_cancel" type="object" string="Cancel" attrs="{'invisible': [('state', 'in', ['done', 'cancelled'])]}"/>
                    <field name="state" widget="statusbar" statusbar_visible="draft,confirmed,done"/>
                </header>
                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="partner_id"/>
                            <field name="date"/>
                        </group>
                        <group>
                            <field name="amount"/>
                            <field name="active" widget="boolean_toggle"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Description">
                            <field name="description" placeholder="Enter description..."/>
                        </page>
                    </notebook>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>
        </field>
    </record>

    <!-- Search View -->
    <record id="MODULE_NAME_search_view" model="ir.ui.view">
        <field name="name">MODULE_NAME.search</field>
        <field name="model">MODULE_NAME.model</field>
        <field name="arch" type="xml">
            <search>
                <field name="name"/>
                <field name="partner_id"/>
                <filter name="filter_draft" string="Draft" domain="[('state', '=', 'draft')]"/>
                <filter name="filter_confirmed" string="Confirmed" domain="[('state', '=', 'confirmed')]"/>
                <filter name="filter_done" string="Done" domain="[('state', '=', 'done')]"/>
                <separator/>
                <filter name="filter_active" string="Active" domain="[('active', '=', True)]"/>
                <group expand="0" string="Group By">
                    <filter name="group_partner" string="Partner" context="{'group_by': 'partner_id'}"/>
                    <filter name="group_state" string="State" context="{'group_by': 'state'}"/>
                    <filter name="group_date" string="Date" context="{'group_by': 'date'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Action -->
    <record id="MODULE_NAME_action" model="ir.actions.act_window">
        <field name="name">MODULE_NAME</field>
        <field name="res_model">MODULE_NAME.model</field>
        <field name="view_mode">tree,form</field>
        <field name="search_view_id" ref="MODULE_NAME_search_view"/>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                Create your first record
            </p>
        </field>
    </record>

    <!-- Menu -->
    <menuitem id="MODULE_NAME_menu_root" name="MODULE_NAME" sequence="10"/>
    <menuitem id="MODULE_NAME_menu_main" name="Records" parent="MODULE_NAME_menu_root" action="MODULE_NAME_action" sequence="10"/>
</odoo>`;
  }

  private getOdooControllerTemplate(): string {
    return `# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json

class MODULE_NAMEController(http.Controller):

    @http.route('/MODULE_NAME/api/items', type='http', auth='public', methods=['GET'], cors='*')
    def get_items(self, **kwargs):
        """Get all items"""
        items = request.env['MODULE_NAME.model'].sudo().search([])
        data = []
        for item in items:
            data.append({
                'id': item.id,
                'name': item.name,
                'description': item.description,
                'state': item.state,
            })
        return request.make_response(
            json.dumps({'status': 'success', 'data': data}),
            headers={'Content-Type': 'application/json'}
        )

    @http.route('/MODULE_NAME/api/item/<int:item_id>', type='http', auth='public', methods=['GET'], cors='*')
    def get_item(self, item_id, **kwargs):
        """Get single item"""
        item = request.env['MODULE_NAME.model'].sudo().browse(item_id)
        if not item.exists():
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Item not found'}),
                headers={'Content-Type': 'application/json'},
                status=404
            )

        data = {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'state': item.state,
            'partner': item.partner_id.name if item.partner_id else None,
            'amount': item.amount,
            'date': str(item.date) if item.date else None,
        }

        return request.make_response(
            json.dumps({'status': 'success', 'data': data}),
            headers={'Content-Type': 'application/json'}
        )

    @http.route('/MODULE_NAME/api/item', type='json', auth='user', methods=['POST'], cors='*')
    def create_item(self, **kwargs):
        """Create new item"""
        try:
            vals = {
                'name': kwargs.get('name'),
                'description': kwargs.get('description'),
                'partner_id': kwargs.get('partner_id'),
            }
            item = request.env['MODULE_NAME.model'].create(vals)
            return {
                'status': 'success',
                'data': {
                    'id': item.id,
                    'name': item.name
                }
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/MODULE_NAME/page', type='http', auth='public', website=True)
    def MODULE_NAME_page(self, **kwargs):
        """Render website page"""
        items = request.env['MODULE_NAME.model'].sudo().search([('state', '=', 'done')])
        return request.render('MODULE_NAME.page_template', {
            'items': items,
        })`;
  }

  private getOdooSecurityTemplate(): string {
    return this.getOdooAccessCsv('module_name');
  }

  private getOdooManifest(moduleName: string, version: string, features: string[]): string {
    const depends = ['base'];
    if (features.includes('website')) depends.push('website');
    if (features.includes('sale')) depends.push('sale');
    if (features.includes('purchase')) depends.push('purchase');
    if (features.includes('account')) depends.push('account');
    if (features.includes('stock')) depends.push('stock');

    const data = ['security/ir.model.access.csv'];
    if (features.includes('security')) data.unshift('security/security.xml');
    if (features.includes('views')) data.push(`views/${moduleName}_views.xml`);
    if (features.includes('reports')) data.push(`reports/${moduleName}_reports.xml`);

    return `# -*- coding: utf-8 -*-
{
    'name': '${this.toPascalCase(moduleName)}',
    'version': '${version}.0.1.0.0',
    'summary': 'Short summary of ${moduleName}',
    'description': '''
        Long description of module's purpose
    ''',
    'category': 'Uncategorized',
    'author': 'Your Name',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': ${JSON.stringify(depends)},
    'data': ${JSON.stringify(data, null, 8).replace(/"/g, "'")},
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}`;
  }

  private getOdooInit(features: string[]): string {
    const imports = [];
    if (features.includes('models') || features.includes('model')) {
      imports.push('from . import models');
    }
    if (features.includes('controllers') || features.includes('controller')) {
      imports.push('from . import controllers');
    }
    if (features.includes('wizard')) {
      imports.push('from . import wizard');
    }
    return `# -*- coding: utf-8 -*-\n${imports.join('\n')}`;
  }

  private getOdooAccessCsv(moduleName: string): string {
    return `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_${moduleName}_model_user,${moduleName}.model.user,model_${moduleName.replace(/\./g, '_')}_model,base.group_user,1,0,0,0
access_${moduleName}_model_manager,${moduleName}.model.manager,model_${moduleName.replace(/\./g, '_')}_model,base.group_system,1,1,1,1`;
  }

  private getOdooSecurityGroupsTemplate(moduleName: string): string {
    return `<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <!-- Categories -->
        <record id="module_category_${moduleName}" model="ir.module.category">
            <field name="name">${this.toPascalCase(moduleName)}</field>
            <field name="description">Category for ${moduleName}</field>
            <field name="sequence">10</field>
        </record>

        <!-- Groups -->
        <record id="group_${moduleName}_user" model="res.groups">
            <field name="name">${this.toPascalCase(moduleName)} User</field>
            <field name="category_id" ref="module_category_${moduleName}"/>
            <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
        </record>

        <record id="group_${moduleName}_manager" model="res.groups">
            <field name="name">${this.toPascalCase(moduleName)} Manager</field>
            <field name="category_id" ref="module_category_${moduleName}"/>
            <field name="implied_ids" eval="[(4, ref('group_${moduleName}_user'))]"/>
        </record>

        <!-- Record Rules -->
        <record id="rule_${moduleName}_user" model="ir.rule">
            <field name="name">${this.toPascalCase(moduleName)}: User can only see own records</field>
            <field name="model_id" ref="model_${moduleName.replace(/\./g, '_')}_model"/>
            <field name="domain_force">[('create_uid', '=', user.id)]</field>
            <field name="groups" eval="[(4, ref('group_${moduleName}_user'))]"/>
        </record>

        <record id="rule_${moduleName}_manager" model="ir.rule">
            <field name="name">${this.toPascalCase(moduleName)}: Manager can see all records</field>
            <field name="model_id" ref="model_${moduleName.replace(/\./g, '_')}_model"/>
            <field name="domain_force">[(1, '=', 1)]</field>
            <field name="groups" eval="[(4, ref('group_${moduleName}_manager'))]"/>
        </record>
    </data>
</odoo>`;
  }

  private generateOdooAccessCsv(models: string[], groups: string[]): string {
    const lines = ['id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink'];

    for (const model of models) {
      const modelId = model.replace(/\./g, '_');

      // Default user access
      lines.push(`access_${modelId}_user,${model}.user,model_${modelId},base.group_user,1,0,0,0`);

      // Manager access
      lines.push(`access_${modelId}_manager,${model}.manager,model_${modelId},base.group_system,1,1,1,1`);

      // Custom groups
      for (const group of groups) {
        lines.push(`access_${modelId}_${group},${model}.${group},model_${modelId},group_${group},1,1,1,0`);
      }
    }

    return lines.join('\n');
  }

  private generateOdooSecurityXml(models: string[], groups: string[]): string {
    return this.getOdooSecurityGroupsTemplate(models[0]?.split('.')[0] || 'module');
  }

  // Helper methods
  private detectLanguage(filePath: string): string {
    const ext = path.extname(filePath).toLowerCase();
    const languageMap: Record<string, string> = {
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.py': 'python',
      '.java': 'java',
      '.cpp': 'cpp',
      '.c': 'c',
      '.cs': 'csharp',
      '.rb': 'ruby',
      '.go': 'go',
      '.rs': 'rust',
      '.php': 'php'
    };
    return languageMap[ext] || 'unknown';
  }

  private toPascalCase(str: string): string {
    return str
      .replace(/[_-]/g, ' ')
      .replace(/\w\S*/g, txt => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase())
      .replace(/\s/g, '');
  }

  private generateReactBoilerplate(template: string, name: string, options: any): string {
    const templates: Record<string, string> = {
      component: this.getReactComponentTemplate(),
      hook: this.getReactHookTemplate(),
      context: this.getReactContextTemplate(),
      redux: this.getReduxTemplate()
    };

    const code = templates[template] || this.getReactComponentTemplate();
    return code.replace(/COMPONENT_NAME|HOOK_NAME|CONTEXT_NAME|SLICE_NAME/g, name);
  }

  private generateVueBoilerplate(template: string, name: string, options: any): string {
    const templates: Record<string, string> = {
      component: this.getVueComponentTemplate(),
      store: this.getVueStoreTemplate(),
      composable: this.getVueComposableTemplate()
    };

    const code = templates[template] || this.getVueComponentTemplate();
    return code.replace(/COMPONENT_NAME|STORE_NAME|COMPOSABLE_NAME/g, name);
  }

  private generateNodeBoilerplate(template: string, name: string, options: any): string {
    const templates: Record<string, string> = {
      express: this.getExpressTemplate(),
      api: this.getApiTemplate(),
      middleware: this.getMiddlewareTemplate(),
      model: this.getModelTemplate()
    };

    const code = templates[template] || this.getExpressTemplate();
    return code.replace(/MIDDLEWARE_NAME|MODEL_NAME/g, name);
  }

  private generatePythonBoilerplate(framework: string, template: string, name: string, options: any): string {
    if (framework === 'django') {
      return this.getDjangoModelTemplate().replace(/MODEL_NAME/g, name);
    } else if (framework === 'flask') {
      return this.getFlaskApiTemplate();
    }

    return this.getPythonClassTemplate().replace(/CLASS_NAME/g, name);
  }

  private async generateOdooBoilerplate(template: string, name: string, options: any): Promise<string> {
    const templates: Record<string, string> = {
      module: this.getOdooModuleTemplate(),
      model: this.getOdooModelTemplate(),
      view: this.getOdooViewTemplate(),
      controller: this.getOdooControllerTemplate(),
      security: this.getOdooSecurityTemplate()
    };

    const code = templates[template] || this.getOdooModuleTemplate();
    return code.replace(/MODULE_NAME|ModelName/g, name);
  }

  private generateGenericBoilerplate(type: string, name: string, options: any): string {
    return `// Generic ${type} boilerplate for ${name}\n// TODO: Implement ${type} logic`;
  }

  private generateJavaScriptTests(content: string, framework: string, coverage: string): string {
    // Parse functions and classes from content
    const functions = this.extractFunctions(content);
    const classes = this.extractClasses(content);

    if (framework === 'jest') {
      return this.generateJestTests(functions, classes, coverage);
    } else if (framework === 'mocha') {
      return this.generateMochaTests(functions, classes, coverage);
    }

    return '// Test framework not supported';
  }

  private generatePythonTests(content: string, framework: string, coverage: string): string {
    const template = this.getPythonTestTemplate();
    // Customize based on content analysis
    return template;
  }

  private generateJavaTests(content: string, coverage: string): string {
    return `import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class GeneratedTest {
    @Test
    void testExample() {
        // Add test implementation
        assertTrue(true);
    }
}`;
  }

  private extractFunctions(content: string): string[] {
    const functionPattern = /(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\()/g;
    const matches = [];
    let match;
    while ((match = functionPattern.exec(content)) !== null) {
      matches.push(match[1] || match[2]);
    }
    return matches.filter(Boolean);
  }

  private extractClasses(content: string): string[] {
    const classPattern = /class\s+(\w+)/g;
    const matches = [];
    let match;
    while ((match = classPattern.exec(content)) !== null) {
      matches.push(match[1]);
    }
    return matches;
  }

  private generateJestTests(functions: string[], classes: string[], coverage: string): string {
    let tests = `describe('Generated Tests', () => {\n`;

    for (const func of functions) {
      tests += `  describe('${func}', () => {\n`;
      tests += `    it('should execute without errors', () => {\n`;
      tests += `      // Add test for ${func}\n`;
      tests += `      expect(true).toBe(true);\n`;
      tests += `    });\n`;

      if (coverage === 'comprehensive' || coverage === 'edge-cases') {
        tests += `    it('should handle edge cases', () => {\n`;
        tests += `      // Add edge case tests\n`;
        tests += `    });\n`;
      }

      tests += `  });\n\n`;
    }

    for (const cls of classes) {
      tests += `  describe('${cls}', () => {\n`;
      tests += `    let instance;\n\n`;
      tests += `    beforeEach(() => {\n`;
      tests += `      instance = new ${cls}();\n`;
      tests += `    });\n\n`;
      tests += `    it('should create an instance', () => {\n`;
      tests += `      expect(instance).toBeDefined();\n`;
      tests += `    });\n`;
      tests += `  });\n\n`;
    }

    tests += `});\n`;
    return tests;
  }

  private generateMochaTests(functions: string[], classes: string[], coverage: string): string {
    let tests = `const { expect } = require('chai');\n\n`;
    tests += `describe('Generated Tests', () => {\n`;

    for (const func of functions) {
      tests += `  describe('${func}', () => {\n`;
      tests += `    it('should execute without errors', () => {\n`;
      tests += `      // Add test for ${func}\n`;
      tests += `      expect(true).to.be.true;\n`;
      tests += `    });\n`;
      tests += `  });\n\n`;
    }

    tests += `});\n`;
    return tests;
  }

  private generateJSDoc(content: string, includeExamples: boolean): string {
    // Simple JSDoc generation
    const lines = content.split('\n');
    const documented: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (/function\s+\w+|const\s+\w+\s*=.*=>/.test(line)) {
        documented.push('/**');
        documented.push(' * Description of the function');
        documented.push(' * @param {*} param - Parameter description');
        documented.push(' * @returns {*} Return description');

        if (includeExamples) {
          documented.push(' * @example');
          documented.push(' * // Example usage');
          documented.push(' * functionName(param);');
        }

        documented.push(' */');
      }

      documented.push(line);
    }

    return documented.join('\n');
  }

  private generateDocstrings(content: string, includeExamples: boolean): string {
    // Python docstring generation
    const lines = content.split('\n');
    const documented: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      documented.push(line);

      if (/^\s*def\s+\w+/.test(line)) {
        const indent = line.match(/^\s*/)?.[0] || '';
        documented.push(`${indent}    """`);
        documented.push(`${indent}    Description of the function.`);
        documented.push(`${indent}    `);
        documented.push(`${indent}    Args:`);
        documented.push(`${indent}        param: Parameter description`);
        documented.push(`${indent}    `);
        documented.push(`${indent}    Returns:`);
        documented.push(`${indent}        Return description`);

        if (includeExamples) {
          documented.push(`${indent}    `);
          documented.push(`${indent}    Example:`);
          documented.push(`${indent}        >>> function_name(param)`);
          documented.push(`${indent}        expected_output`);
        }

        documented.push(`${indent}    """`);
      }
    }

    return documented.join('\n');
  }

  private generateMarkdownDocs(content: string, language: string, includeExamples: boolean): string {
    const functions = this.extractFunctions(content);
    const classes = this.extractClasses(content);

    let markdown = `# API Documentation\n\n`;

    if (classes.length > 0) {
      markdown += `## Classes\n\n`;
      for (const cls of classes) {
        markdown += `### ${cls}\n\n`;
        markdown += `Description of ${cls} class.\n\n`;

        if (includeExamples) {
          markdown += `**Example:**\n\`\`\`${language}\n`;
          markdown += `const instance = new ${cls}();\n`;
          markdown += `\`\`\`\n\n`;
        }
      }
    }

    if (functions.length > 0) {
      markdown += `## Functions\n\n`;
      for (const func of functions) {
        markdown += `### ${func}\n\n`;
        markdown += `Description of ${func} function.\n\n`;
        markdown += `**Parameters:**\n- \`param\` - Parameter description\n\n`;
        markdown += `**Returns:**\n- Return description\n\n`;

        if (includeExamples) {
          markdown += `**Example:**\n\`\`\`${language}\n`;
          markdown += `${func}(param);\n`;
          markdown += `\`\`\`\n\n`;
        }
      }
    }

    return markdown;
  }

  private generateOpenApiDocs(content: string, includeExamples: boolean): string {
    return `openapi: 3.0.0
info:
  title: API Documentation
  version: 1.0.0
paths:
  /api/endpoint:
    get:
      summary: Endpoint description
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      type: object`;
  }

  private convertJsToTs(content: string, preserveComments: boolean): string {
    let converted = content;

    // Add type annotations
    converted = converted.replace(/function\s+(\w+)\s*\(/g, 'function $1(');
    converted = converted.replace(/const\s+(\w+)\s*=/g, 'const $1: any =');
    converted = converted.replace(/let\s+(\w+)\s*=/g, 'let $1: any =');

    // Add interface for objects
    converted = `// TypeScript conversion\n${converted}`;

    return converted;
  }

  private convertClassToHooks(content: string): string {
    // Simplified conversion from React class to hooks
    return content
      .replace(/class\s+(\w+)\s+extends\s+React\.Component/, 'const $1 = () =>')
      .replace(/this\.state\s*=\s*{/, 'const [state, setState] = useState({')
      .replace(/this\.setState/, 'setState')
      .replace(/componentDidMount/, 'useEffect(() => {')
      .replace(/render\s*\(\)\s*{/, '');
  }

  private convertCallbacksToPromises(content: string): string {
    // Simplified callback to promise conversion
    return content.replace(
      /(\w+)\((.*?),\s*function\s*\((err,\s*data)\)\s*{/g,
      'new Promise((resolve, reject) => {\n  $1($2, (err, data) => {\n    if (err) reject(err);\n    else resolve(data);\n  });\n}).then(data => {'
    );
  }

  private convertPromisesToAsync(content: string): string {
    // Convert .then() chains to async/await
    return content
      .replace(/\.then\s*\((.*?)\s*=>\s*{/g, ';\nconst $1 = await ')
      .replace(/\.catch\s*\((.*?)\s*=>\s*{/g, ';\n} catch($1) {');
  }

  private convertCommonJsToEsm(content: string): string {
    // Convert CommonJS to ES modules
    return content
      .replace(/const\s+(\w+)\s*=\s*require\(['"](.+)['"]\)/g, "import $1 from '$2'")
      .replace(/const\s+{\s*(.*?)\s*}\s*=\s*require\(['"](.+)['"]\)/g, "import { $1 } from '$2'")
      .replace(/module\.exports\s*=\s*/, 'export default ')
      .replace(/exports\.(\w+)\s*=\s*/, 'export const $1 = ');
  }

  private getProjectStructure(stack: string, features: string[]): any {
    const structures: Record<string, any> = {
      'MERN': {
        directories: [
          'client/src/components',
          'client/src/pages',
          'client/src/utils',
          'client/public',
          'server/controllers',
          'server/models',
          'server/routes',
          'server/middleware',
          'server/config'
        ],
        files: {
          'package.json': this.getMernPackageJson(),
          'client/package.json': this.getReactPackageJson(),
          'server/index.js': this.getExpressTemplate(),
          '.gitignore': this.getGitignore(),
          'README.md': '# MERN Stack Project'
        }
      },
      'Django+React': {
        directories: [
          'backend/api',
          'backend/core',
          'frontend/src/components',
          'frontend/src/pages',
          'frontend/src/services'
        ],
        files: {
          'backend/manage.py': '#!/usr/bin/env python\n# Django manage.py',
          'backend/requirements.txt': 'django>=4.0\ndjangorestframework\ncors-headers',
          'frontend/package.json': this.getReactPackageJson(),
          '.gitignore': this.getGitignore()
        }
      },
      'Vue+FastAPI': {
        directories: [
          'backend/app/api',
          'backend/app/core',
          'backend/app/models',
          'frontend/src/components',
          'frontend/src/views',
          'frontend/src/stores'
        ],
        files: {
          'backend/main.py': 'from fastapi import FastAPI\n\napp = FastAPI()',
          'backend/requirements.txt': 'fastapi\nuvicorn\nsqlalchemy',
          'frontend/package.json': this.getVuePackageJson(),
          '.gitignore': this.getGitignore()
        }
      },
      'Odoo': {
        directories: [
          'addons',
          'config',
          'data',
          'scripts'
        ],
        files: {
          'requirements.txt': '# Odoo dependencies',
          '.gitignore': this.getGitignore(),
          'README.md': '# Odoo Project'
        }
      }
    };

    return structures[stack] || structures['MERN'];
  }

  private getMernPackageJson(): string {
    return JSON.stringify({
      name: 'mern-app',
      version: '1.0.0',
      scripts: {
        dev: 'concurrently "npm run server" "npm run client"',
        server: 'cd server && npm start',
        client: 'cd client && npm start'
      },
      devDependencies: {
        concurrently: '^7.0.0'
      }
    }, null, 2);
  }

  private getReactPackageJson(): string {
    return JSON.stringify({
      name: 'react-app',
      version: '1.0.0',
      dependencies: {
        react: '^18.0.0',
        'react-dom': '^18.0.0',
        'react-router-dom': '^6.0.0',
        axios: '^1.0.0'
      },
      scripts: {
        start: 'react-scripts start',
        build: 'react-scripts build',
        test: 'react-scripts test'
      }
    }, null, 2);
  }

  private getVuePackageJson(): string {
    return JSON.stringify({
      name: 'vue-app',
      version: '1.0.0',
      dependencies: {
        vue: '^3.0.0',
        'vue-router': '^4.0.0',
        pinia: '^2.0.0',
        axios: '^1.0.0'
      },
      scripts: {
        dev: 'vite',
        build: 'vite build',
        preview: 'vite preview'
      }
    }, null, 2);
  }

  private getGitignore(): string {
    return `# Dependencies
node_modules/
*.pyc
__pycache__/

# Environment
.env
.env.local
*.env

# Build
dist/
build/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp

# Logs
*.log
npm-debug.log*

# OS
.DS_Store
Thumbs.db`;
  }
}