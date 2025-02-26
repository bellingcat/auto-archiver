import * as React from 'react';
import { useEffect, useState } from 'react';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import { modules, steps, configs, module_types } from './schema.json';
import { 
  Checkbox,
  Select,
  MenuItem,
  FormControl,
  FormControlLabel,
  InputLabel,
  FormHelperText,
  Stack,
  TextField,
  Card,
  CardContent,
  CardActions,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
} from '@mui/material';
import Grid from '@mui/material/Grid2';

import Accordion from '@mui/material/Accordion';
import AccordionDetails from '@mui/material/AccordionDetails';
import AccordionSummary from '@mui/material/AccordionSummary';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import ReactMarkdown from 'react-markdown';
import { parseDocument, ParsedNode, Document } from 'yaml'
import { set } from 'yaml/dist/schema/yaml-1.1/set';

Object.defineProperty(String.prototype, 'capitalize', {
  value: function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
  },
  enumerable: false
});

function FileDrop({ setYamlFile }) {

  const [showError, setShowError] = useState(false);
  const [label, setLabel] = useState("Drag and drop your orchestration.yaml file here, or click to select a file.");

  function openYAMLFile(event: any) {
    let file = event.target.files[0];
    if (file.type !== 'application/x-yaml') {
      setShowError(true);
      setLabel("Invalid type, only YAML files are accepted.")
      return;
    }
    let reader = new FileReader();
    reader.onload = function(e) {
      let contents = e.target.result;
      try {
        let document = parseDocument(contents);
        if (document.errors.length > 0) {
          // not a valid yaml file
          setShowError(true);
          setLabel("Invalid file. Make sure your Orchestration is a valid YAML file with a 'steps' section in it.")
          return;
        } else {
          setShowError(false);
          setLabel("File loaded successfully.")
        }
        setYamlFile(document);
      } catch (e) {
        console.error(e);
      }
    }
    reader.readAsText(file);
  }
  return (
    <>
    <div style={{width:'100%', border:'dashed', textAlign:'center', borderWidth:'1px', padding:'20px'}}>

      <input name="file" type="file" accept=".yaml" onChange={openYAMLFile}  />
      <Typography style={{marginTop:'20px' }} variant="body1" color={showError ? 'error' : ''} >
        {label}
      </Typography>
    </div>
    </>
  );
}


function ModuleCheckbox({ module, toggleModule, enabledModules, configValues }: { module: object, toggleModule: any, enabledModules: any, configValues: any }) {
  let name = module.name;
  const [helpOpen, setHelpOpen] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);
  if (name == 'metadata_enricher') {
    console.log("hi");
  }
  return (
  <>
    <Card>
      <CardContent>
      <FormControlLabel
      control={<Checkbox id={name} onClick={toggleModule} checked={enabledModules.includes(name)} />}
      label={module.display_name} />
      </CardContent>
      <CardActions>
        <Button size="small" onClick={() => setHelpOpen(true)}>Help</Button>
        {enabledModules.includes(name) && module.configs && name != 'cli_feeder' ? (
      <Button size="small" onClick={() => setConfigOpen(true)}>Configure</Button>
      ) : null}
      </CardActions>
      </Card>
      <Dialog
      open={helpOpen}
      onClose={() => setHelpOpen(false)}
      maxWidth="lg"
      >
        <DialogTitle>
          {module.display_name}
        </DialogTitle>
        <DialogContent>
        <ReactMarkdown>
          {module.manifest.description.split("\n").map((line: string) => line.trim()).join("\n")}
          </ReactMarkdown>
        </DialogContent>
      </Dialog>
      {module.configs && name != 'cli_feeder' && <ConfigPanel module={module} open={configOpen} setOpen={setConfigOpen} configValues={configValues[module.name]} />}
    </>
  )
}


function ConfigPanel({ module, open, setOpen, configValues }: { module: any, open: boolean, setOpen: any, configValues: any }) {
  return (
    <>
        <Dialog
        key={module}
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="lg"
        >
          <DialogTitle>
            {module.display_name}
          </DialogTitle>
          <DialogContent>
          <Stack key={module} direction="column" spacing={1}>
          {Object.keys(module.configs).map((config_value: any) => {
            let config_args = module.configs[config_value];
            let config_name = config_value.replace(/_/g," ");
            return (
              <Box key={config_value}>
                <FormControl size="small">
                { config_args.type === 'bool' ?                
                  <FormControlLabel style={{ textTransform: 'capitalize'}} control={<Checkbox checked={configValues[config_value]} size="small" id={`${module}.${config_value}`} />} label={config_name} />
                  :
                  ( config_args.type === 'int' ?
                    <TextField size="small" id={`${module}.${config_value}`} label={config_name.capitalize()} value={configValues[config_value]} type="number" />
                    :
                  (
                    config_args.choices !== undefined ?
                    <>
                    <InputLabel>{config_name}</InputLabel>
                    <Select size="small" id={`${module}.${config_value}`}
                      defaultValue={config_args.default} value={configValues[config_value] || ''}>
                      {config_args.choices.map((choice: any) => {
                        return (
                          <MenuItem key={`${module}.${config_value}.${choice}`} 
                          value={choice} selected={config_args.default === choice}>{choice}</MenuItem>
                        );
                      })}
                    </Select>
                    </>
                    :
                      <TextField size="small" id={`${module}.${config_value}`} value={configValues[config_value] || ''} label={config_name.capitalize()} />
                  )
                )
                }
                  <FormHelperText style={{ textTransform: 'capitalize'}}>{config_args.help}</FormHelperText>
                  </FormControl>
              </Box>
            );
          })}
          </Stack>
          </DialogContent>
        </Dialog>
    </>
  );
}

function ModuleTypes({ stepType, toggleModule, enabledModules, configValues }: { stepType: string, toggleModule: any, enabledModules: any, configValues: any }) {
  const [showError, setShowError] = useState(false);

  const _toggleModule = (event: any) => {
    // make sure that 'feeder' and 'formatter' types only have one value
    let name = event.target.id;
    if (stepType === 'feeder' || stepType === 'formatter') {
      let checked = event.target.checked;
      // check how many modules of this type are enabled
      let modules = steps[stepType].filter((m: string) => (m !== name && enabledModules.includes(m)) || (checked && m === name));
      if (modules.length > 1) {
        setShowError(true);
      } else {
        setShowError(false);
      }
    } else {
      setShowError(false);
    }
    toggleModule(event);
  }
  return (
    <>
      <Typography id={stepType} variant="h6" style={{ textTransform: 'capitalize' }} >
      {stepType}s
      </Typography>
      {showError ? <Typography variant="body1" color="error" >Only one {stepType} can be enabled at a time.</Typography> : null}
      <Grid container spacing={1} key={stepType}>
      {steps[stepType].map((name: string) => {
          let m = modules[name];
          return (
            <Grid key={name} size={{ xs: 6, sm: 4, md: 3 }}>
            <ModuleCheckbox key={name} module={m} toggleModule={_toggleModule} enabledModules={enabledModules} configValues={configValues} />
            </Grid>
          );
        })}
      </Grid>
  </>
  );
}


export default function App() {
  const [yamlFile, setYamlFile] = useState<Document>(new Document());
  const [enabledModules, setEnabledModules] = useState<[]>([]);
  const [configValues, setConfigValues] = useState<{}>(
    Object.keys(modules).reduce((acc, module) => {
      acc[module] = {};
      return acc;
    }, {})
  );

  const saveSettings = function(copy: boolean = false) {
    // edit the yamlFile

    // generate the steps config
    let stepsConfig = {}
    module_types.forEach((stepType: string) => {
      stepsConfig[stepType] = enabledModules.filter((m: string) => steps[stepType].includes(m));
    }
    );

      // create a yaml file from 
      const finalYaml = {
        'steps': stepsConfig
      };

      Object.keys(configValues).map((module: string) => {
        let module_values = configValues[module];
        if (module_values) {
          finalYaml[module] = module_values;
        }
      });
      let newFile = new Document(finalYaml);
      if (copy) {
        navigator.clipboard.writeText(String(newFile)).then(() => {
          alert("Settings copied to clipboard.");
        });
      } else {
        // offer the file for download
        const blob = new Blob([String(newFile)], { type: 'application/x-yaml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'orchestration.yaml';
        a.click();
      }
    }

  const toggleModule = function (event: any) {
    let module = event.target.id;
    let checked = event.target.checked

    if (checked) {
      setEnabledModules([...enabledModules, module]);
    } else {
      setEnabledModules(enabledModules.filter((m: string) => m !== module));
    }
  }

  useEffect(() => {
    // load the configs, and set the default values if they exist
    let newConfigValues = {};
    Object.keys(modules).map((module: string) => {
      let m = modules[module];
      let configs = m.configs;
      if (!configs) {
        return;
      }
      newConfigValues[module] = {};
      Object.keys(configs).map((config: string) => {
        let config_args = configs[config];
        if (config_args.default !== undefined) {
          newConfigValues[module][config] = config_args.default;
        }
      });
    })
    setConfigValues(newConfigValues); 
  }, []);

  useEffect(() => {
    if (!yamlFile || yamlFile.contents == null) {
      return;
    }

    let settings = yamlFile.toJS();
    // make a deep copy of settings
    let newEnabledModules = Object.keys(settings['steps']).map((step: string) => {
      return settings['steps'][step];
    }).flat();
    newEnabledModules = newEnabledModules.filter((m: string, i: number) => newEnabledModules.indexOf(m) === i);
    setEnabledModules(newEnabledModules);
  }, [yamlFile]);



  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h2" >
          Auto Archiver Settings
        </Typography>
        <Box sx={{ my: 4 }}>
        <Typography variant="h5" >
          1. Select your <pre style={{display:'inline'}}>orchestration.yaml</pre> settings file.
        </Typography>
        <FileDrop setYamlFile={setYamlFile}/>
        </Box>
        <Box sx={{ my: 4 }}>
        <Typography variant="h5" >
          2. Choose the Modules you wish to enable/disable
        </Typography>
          {Object.keys(steps).map((stepType: string) => {
            return (
              <ModuleTypes key={stepType} stepType={stepType} toggleModule={toggleModule} enabledModules={enabledModules} configValues={configValues} />
            );
          })}
        </Box>
        <Box sx={{ my: 4 }}>
        <Typography variant="h5" >
          3. Configure your Enabled Modules
        </Typography>
        <Typography variant="body1" >
          Next to each module you've enabled, you can click 'Configure' to set the module's settings.
        </Typography>
        </Box>
        <Box sx={{ my: 4 }}>
          <Typography variant="h5" >
            4. Save your settings
          </Typography>
          <Button variant="contained" color="primary" onClick={() => saveSettings(true)}>Copy Settings to Clipboard</Button>
          <Button variant="contained" color="primary" onClick={() => saveSettings()}>Save Settings to File</Button>
          </Box>
      </Box>
    </Container>
  );
}
