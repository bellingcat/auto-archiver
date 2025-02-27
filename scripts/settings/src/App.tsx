import * as React from 'react';
import { useEffect, useState } from 'react';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

// 
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy
} from "@dnd-kit/sortable";

import type { DragStartEvent, DragEndEvent, UniqueIdentifier } from "@dnd-kit/core";


import { Module } from './types';

import { modules, steps, module_types } from './schema.json';
import { 
  Stack,
  Button,
} from '@mui/material';
import Grid from '@mui/material/Grid2';

import { parseDocument, Document } from 'yaml'
import StepCard from './StepCard';


function FileDrop({ setYamlFile }: { setYamlFile: React.Dispatch<React.SetStateAction<Document>> }) {

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
      let contents = e.target ? e.target.result : '';
      try {
        let document = parseDocument(contents as string);
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

function ModuleTypes({ stepType, setEnabledModules, enabledModules, configValues }: { stepType: string, setEnabledModules: any, enabledModules: any, configValues: any }) {
  const [showError, setShowError] = useState<boolean>(false);
  const [activeId, setActiveId] = useState<UniqueIdentifier>();
  const [items, setItems] = useState<string[]>([]);

  useEffect(() => {
    setItems(enabledModules[stepType].map(([name, enabled]: [string, boolean]) => name));
  }
  , [enabledModules]);

  const toggleModule = (event: any) => {
    // make sure that 'feeder' and 'formatter' types only have one value
    let name = event.target.id;
    let checked = event.target.checked;
    if (stepType === 'feeder' || stepType === 'formatter') {
      // check how many modules of this type are enabled
      const checkedModules = enabledModules[stepType].filter(([m, enabled]: [string, boolean]) => {
        return (m !== name && enabled) || (checked && m === name)
      });
      if (checkedModules.length > 1) {
        setShowError(true);
      } else {
        setShowError(false);
      }
    } else {
      setShowError(false);
    }
    let newEnabledModules = Object.fromEntries(Object.keys(enabledModules).map((type : string) => {
      return [type, enabledModules[type].map(([m, enabled]: [string, boolean]) => {
        return (m === name) ? [m, checked] : [m, enabled];
      })];
      }
    ));
    setEnabledModules(newEnabledModules);
  }

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates
    })
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveId(undefined);
    const { active, over } = event;

    if (active.id !== over?.id) {
        const oldIndex = items.indexOf(active.id as string);
        const newIndex = items.indexOf(over?.id as string);

        let newArray = arrayMove(items, oldIndex, newIndex);
        // set it also on steps
        let newEnabledModules = { ...enabledModules };
        newEnabledModules[stepType] = enabledModules[stepType].sort((a, b) => {
          return newArray.indexOf(a[0]) - newArray.indexOf(b[0]);
        })
        setEnabledModules(newEnabledModules);
    }
  };
  return (
    <>
    <Box sx={{ my: 4 }}>
      <Typography id={stepType} variant="h6" style={{ textTransform: 'capitalize' }} >
      {stepType}
      </Typography>
      <Typography variant="body1" >
        Select the {stepType} you wish to enable. You can drag and drop them to reorder them.
      </Typography>
      </Box>
      {showError ? <Typography variant="body1" color="error" >Only one {stepType} can be enabled at a time.</Typography> : null}

      <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
      onDragStart={handleDragStart}
    >
      <Grid container spacing={1} key={stepType}>
      <SortableContext items={items} strategy={rectSortingStrategy}>
      {items.map((name: string) => {
          let m: Module = modules[name];
          return (
            <StepCard key={name} type={stepType} module={m} toggleModule={toggleModule} enabledModules={enabledModules} configValues={configValues} />
          );
        })}
                  <DragOverlay>
            {activeId ? (
<div
                style={{
                  width: "100%",
                  height: "100%",
                  backgroundColor: "grey",
                  opacity:0.1,
                }}
              ></div>

            ) : null}
          </DragOverlay>
      </SortableContext>
      </Grid>
      </DndContext>
  </>
  );
}


export default function App() {
  const [yamlFile, setYamlFile] = useState<Document>(new Document());
  const [enabledModules, setEnabledModules] = useState<{}>(Object.fromEntries(Object.keys(steps).map(type => [type, steps[type].map((name: string) => [name, false])])));
  const [configValues, setConfigValues] = useState<{
    [key: string]: {
      [key: string
      ]: any
    }
  }>(
    Object.keys(modules).reduce((acc, module) => {
      acc[module] = {};
      return acc;
    }, {})
  );

  const saveSettings = function(copy: boolean = false) {
    // edit the yamlFile

    // generate the steps config
    let stepsConfig = enabledModules;

      // create a yaml file from 
      const finalYaml = {
        'steps': Object.keys(steps).reduce((acc, stepType: string) => {
          acc[stepType] = stepsConfig[stepType].filter(([name, enabled]: [string, boolean]) => enabled).map(([name, enabled]: [string, boolean]) => name);
          return acc;
        }, {})
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
    let stepSettings = settings['steps'];
    let newEnabledModules = Object.fromEntries(Object.keys(steps).map((type: string) => {
        return [type, steps[type].map((name: string) => {
          return [name, stepSettings[type].indexOf(name) !== -1];
        }).sort((a, b) => {
          let aIndex = stepSettings[type].indexOf(a[0]);
          let bIndex = stepSettings[type].indexOf(b[0]);
          if (aIndex === -1 && bIndex === -1) {
            return a - b;
          }
          if (bIndex === -1) {
            return -1;
          }
          if (aIndex === -1) {
            return 1;
          }
          return aIndex - bIndex;
        })];
      }).sort((a, b) => {
        return module_types.indexOf(a[0]) - module_types.indexOf(b[0]);
      }));
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
              <Box key={stepType} sx={{ my: 4 }}>
              <ModuleTypes stepType={stepType} setEnabledModules={setEnabledModules} enabledModules={enabledModules} configValues={configValues} />
              </Box>
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
          <Stack direction="row" spacing={2} sx={{ my: 2 }}>
          <Button variant="contained" color="primary" onClick={() => saveSettings(true)}>Copy Settings to Clipboard</Button>
          <Button variant="contained" color="primary" onClick={() => saveSettings()}>Save Settings to File</Button>
          </Stack>
          </Box>
      </Box>
    </Container>
  );
}
