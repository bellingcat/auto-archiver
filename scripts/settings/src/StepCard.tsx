import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import ReactMarkdown from 'react-markdown';

import { CSS } from "@dnd-kit/utilities";

import {
    Card,
    CardActions,
    CardHeader,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    Box,
    IconButton,
    Checkbox,
    Select,
    MenuItem,
    FormControl,
    FormControlLabel,
    FormHelperText,
    TextField,
    Stack,
    Typography,
} from '@mui/material';
import Grid from '@mui/material/Grid2';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import HelpIconOutlined from '@mui/icons-material/HelpOutline';
import { Module, Config } from "./types";


// adds 'capitalize' method to String prototype
declare global {
    interface String {
        capitalize(): string;
    }
}
String.prototype.capitalize = function (this: string) {
    return this.charAt(0).toUpperCase() + this.slice(1);
};

const StepCard = ({
    type,
    module,
    toggleModule,
    enabledModules,
    configValues
}: {
    type: string,
    module: Module,
    toggleModule: any,
    enabledModules: any,
    configValues: any
}) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id: module.name });


    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? "100" : "auto",
        opacity: isDragging ? 0.3 : 1
    };

    let name = module.name;
    const [helpOpen, setHelpOpen] = useState(false);
    const [configOpen, setConfigOpen] = useState(false);
    const enabled = enabledModules[type].find((m: any) => m[0] === name)[1];

    return (
        <Grid ref={setNodeRef} size={{ xs: 6, sm: 4, md: 3 }} style={style}>
            <Card >
                <CardHeader
                    title={
                        <FormControlLabel
                            style={{paddingRight: '0 !important'}}
                            control={<Checkbox sx={{paddingTop:0, paddingBottom:0}} id={name} onClick={toggleModule} checked={enabled} />}
                            label={module.display_name} />
                    }
                />
                <CardActions>
                    <Box sx={{ justifyContent: 'space-between', display: 'flex', width: '100%' }}>
                        <Box>
                    <IconButton size="small" onClick={() => setHelpOpen(true)}>
                        <HelpIconOutlined />
                    </IconButton>
                    {enabled && module.configs && name != 'cli_feeder' ? (
                        <Button size="small" onClick={() => setConfigOpen(true)}>Configure</Button>
                    ) : null}
                    </Box>
                        <IconButton size="small" sx={{textAlight: 'right', cursor: 'grab' }}  {...listeners} {...attributes}>
                            <DragIndicatorIcon />
                        </IconButton>
                        </Box>
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
            {module.configs && name != 'cli_feeder' && <ConfigPanel module={module} open={configOpen} setOpen={setConfigOpen} configValues={configValues} />}
        </Grid>
    )
}

function ConfigField({ config_value, module, configValues }: { config_value: any, module: Module, configValues: any }) {
    function setConfigValue(config: any, value: any) {
        configValues[module.name][config] = value;
    }
    const config_args: Config = module.configs[config_value];
    const config_name: string = config_value.replace(/_/g, " ");
    const config_display_name = config_name.capitalize();
    const value = configValues[module.name][config_value] || config_args.default;
    return (
        <Box>
            <Typography variant='body1' style={{ fontWeight: 'bold' }}>{config_display_name} {config_args.required && (`(required)`)} </Typography>
            <FormControl size="small">
                {config_args.type === 'bool' ?
                    <FormControlLabel control={
                        <Checkbox defaultChecked={value} size="small" id={`${module}.${config_value}`}
                            onChange={(e) => {
                                setConfigValue(config_value, e.target.checked);
                            }}
                        />} label={config_args.help}
                    />
                    :
                    (
                        config_args.choices !== undefined ?
                            <Select size="small" id={`${module}.${config_value}`}
                                defaultValue={value}
                                onChange={(e) => {
                                    setConfigValue(config_value, e.target.value);
                                }}
                            >
                                {config_args.choices.map((choice: any) => {
                                    return (
                                        <MenuItem key={`${module}.${config_value}.${choice}`}
                                            value={choice}>{choice}</MenuItem>
                                    );
                                })}
                            </Select>
                            :
                            (config_args.type === 'json_loader' ?
                                <TextField multiline size="small" id={`${module}.${config_value}`} defaultValue={JSON.stringify(value, null, 2)} rows={6} onChange={
                                    (e) => {
                                        try {
                                            let val = JSON.parse(e.target.value);
                                            setConfigValue(config_value, val);
                                        } catch (e) {
                                            console.log(e);
                                        }
                                    }
                                } />
                                :
                                <TextField size="small" id={`${module}.${config_value}`} defaultValue={value} type={config_args.type === 'int' ? 'number' : 'text'}
                                    onChange={(e) => {
                                        setConfigValue(config_value, e.target.value);
                                    }}
                                    required={config_args.required}
                                />
                            )
                    )
                }
                {config_args.type !== 'bool' && (
                    <FormHelperText >{config_args.help.capitalize()}</FormHelperText>
                )}
            </FormControl>
        </Box>
    )
}

function ConfigPanel({ module, open, setOpen, configValues }: { module: Module, open: boolean, setOpen: any, configValues: any }) {

    return (
        <>
            <Dialog
                open={open}
                onClose={() => setOpen(false)}
                maxWidth="lg"
            >
                <DialogTitle>
                    {module.display_name}
                </DialogTitle>
                <DialogContent>
                    <Stack direction="column" spacing={1}>
                        {Object.keys(module.configs).map((config_value: any) => {
                            return (
                                <ConfigField key={config_value} config_value={config_value} module={module} configValues={configValues} />
                            );
                        })}
                    </Stack>
                </DialogContent>
            </Dialog>
        </>
    );
}

export default StepCard;