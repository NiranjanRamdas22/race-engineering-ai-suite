import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from collections import deque
from runtime import EngineerRuntime

class RaceEngineerGUI:
    def __init__(self):
        self.root=tk.Tk();self.root.title('AI Race Engineer');self.root.geometry('1080x720');self.root.minsize(390,640);self.root.configure(bg='#08090a')
        style=ttk.Style();style.theme_use('clam');style.configure('.',background='#151719',foreground='#f7f8f8',font=('Arial',11));style.configure('TButton',padding=6);style.map('TButton',background=[('active','#d71920')])
        style.configure('Accent.TButton',background='#d71920');style.configure('TCombobox',fieldbackground='#20242a',foreground='#f7f8f8');style.map('TCombobox',fieldbackground=[('readonly','#20242a')],foreground=[('readonly','#f7f8f8')],selectbackground=[('readonly','#20242a')],selectforeground=[('readonly','#f7f8f8')])
        self.viewport=tk.Canvas(self.root,bg='#08090a',highlightthickness=0);scroll=ttk.Scrollbar(self.root,orient='vertical',command=self.viewport.yview);scroll.pack(side='right',fill='y');self.viewport.pack(side='left',fill='both',expand=True);self.viewport.configure(yscrollcommand=scroll.set)
        self.body=ttk.Frame(self.viewport);self.body_window=self.viewport.create_window((0,0),window=self.body,anchor='nw')
        self.viewport.bind('<Configure>',self.resize_body);self.body.bind('<Configure>',lambda e:self.viewport.configure(scrollregion=self.viewport.bbox('all')))
        self.root.bind('<MouseWheel>',lambda e:self.viewport.yview_scroll(-int(e.delta/120),'units'))
        self.runtime=EngineerRuntime();self.history=deque(maxlen=100);self.latest=tk.StringVar(value='Ready. Start the simulation or import a recorded lap.')
        self.controls=ttk.Frame(self.body);self.controls.pack(fill='x',padx=12,pady=12)
        for c in range(3):self.controls.columnconfigure(c,weight=1)
        ttk.Button(self.controls,text='Start / Resume',command=self.start,style='Accent.TButton').grid(row=0,column=0,sticky='ew')
        ttk.Button(self.controls,text='Pause',command=self.pause).grid(row=0,column=1,sticky='ew',padx=4)
        ttk.Button(self.controls,text='Reset',command=self.reset).grid(row=0,column=2,sticky='ew')
        self.scenario=tk.StringVar(value='Balanced');ttk.Label(self.controls,text='Scenario').grid(row=1,column=0,sticky='w')
        ttk.Combobox(self.controls,textvariable=self.scenario,values=['Balanced','Lockup practice'],state='readonly',width=18).grid(row=1,column=1,columnspan=2,sticky='ew',pady=5)
        ttk.Button(self.controls,text='Import recorded lap',command=self.load).grid(row=2,column=0,sticky='ew')
        ttk.Button(self.controls,text='Import reference lap',command=self.load_reference).grid(row=2,column=1,sticky='ew')
        self.rate=tk.StringVar(value='1×');ttk.Combobox(self.controls,textvariable=self.rate,values=['1×','2×','4×'],state='readonly',width=4).grid(row=2,column=2,sticky='ew')
        ttk.Button(self.controls,text='Use simulation',command=self.use_simulation).grid(row=3,column=0,columnspan=3,sticky='ew',pady=4)
        voicebar=ttk.Frame(self.body);voicebar.pack(fill='x',padx=12)
        self.voice=tk.BooleanVar(value=False);ttk.Checkbutton(voicebar,text='Enable voice feedback',variable=self.voice,command=self.voice_changed).pack(side='left')
        self.effects=tk.BooleanVar(value=False);ttk.Checkbutton(voicebar,text='Radio tone',variable=self.effects).pack(side='left')
        ttk.Label(voicebar,text='Volume').pack(side='left');self.volume=tk.DoubleVar(value=80);ttk.Scale(voicebar,from_=0,to=100,variable=self.volume).pack(side='left',fill='x',expand=True)
        self.status=tk.StringVar(value='Paused • telemetry simulation • Rules coaching');ttk.Label(self.body,textvariable=self.status,wraplength=330).pack(fill='x',padx=12,pady=8)
        self.panels=ttk.Frame(self.body);self.panels.pack(fill='both',expand=True,padx=12,pady=(0,12));self.panels.columnconfigure(0,weight=1);self.panels.columnconfigure(1,weight=1);self.panels.rowconfigure(0,weight=1)
        self.telemetry=ttk.Frame(self.panels,padding=10);self.radio=ttk.Frame(self.panels,padding=10)
        self.speed=tk.StringVar(value='0 km/h');ttk.Label(self.telemetry,textvariable=self.speed,font=('Arial',36,'bold'),foreground='#00d8ec').pack(anchor='w')
        self.details=tk.StringVar(value='Gear — • Throttle — • Brake —');ttk.Label(self.telemetry,textvariable=self.details,wraplength=330).pack(anchor='w',pady=10)
        self.corner=tk.StringVar(value='No active telemetry');self.corner_label=ttk.Label(self.telemetry,textvariable=self.corner,wraplength=330);self.corner_label.pack(fill='x',pady=5)
        self.guidance=tk.StringVar(value='Delta / braking / line: unavailable');ttk.Label(self.telemetry,textvariable=self.guidance,wraplength=300).pack(fill='x')
        self.tires={}
        for key,name in [('FL','Front left'),('FR','Front right'),('RL','Rear left'),('RR','Rear right')]:
            var=tk.StringVar(value=f'{name}: temperature —; remaining —');ttk.Label(self.telemetry,textvariable=var,wraplength=330).pack(anchor='w',pady=7);self.tires[key]=(name,var)
        ttk.Label(self.radio,text='Latest coaching message',font=('Arial',15,'bold')).pack(anchor='w');self.latest_label=ttk.Label(self.radio,textvariable=self.latest,wraplength=330);self.latest_label.pack(fill='x',pady=10)
        self.radio_log=tk.Text(self.radio,height=8,width=20,bg='#08090a',fg='#d9dde3',font=('Arial',11),wrap='word',state='disabled',takefocus=True);self.radio_log.pack(fill='both',expand=True)
        self.root.bind('<Configure>',self.layout);self.root.protocol('WM_DELETE_WINDOW',self.close);self.layout();self.runtime.start_workers();self.root.after(100,self.poll)
    def resize_body(self,event=None):
        self.viewport.itemconfigure(self.body_window,width=self.viewport.winfo_width())
        self.viewport.itemconfigure(self.body_window,height=max(self.body.winfo_reqheight(),self.viewport.winfo_height()))
        self.viewport.configure(scrollregion=self.viewport.bbox('all'))
    def layout(self,event=None):
        if event is not None and event.widget is not self.root:return
        narrow=self.root.winfo_width()<750
        self.telemetry.grid(row=0,column=0,sticky='nsew',padx=3,pady=3)
        self.radio.grid(row=1 if narrow else 0,column=0 if narrow else 1,sticky='nsew',padx=3,pady=3)
        self.panels.rowconfigure(1,weight=1 if narrow else 0)
        width=max(250,(self.root.winfo_width()-70) if narrow else (self.root.winfo_width()-80)//2)
        self.corner_label.configure(wraplength=width);self.latest_label.configure(wraplength=width)
        self.root.after_idle(self.resize_body)
    def start(self):
        self.runtime.playback_speed=int(self.rate.get().replace('×',''));self.runtime.playing=True
    def pause(self):self.runtime.playing=False
    def reset(self):
        self.runtime.reset(self.scenario.get());self.history.clear();self.latest.set('Reset. Ready for a new run.');self.speed.set('0 km/h');self.details.set('Gear — • Throttle — • Brake —');self.corner.set('No active telemetry');self.guidance.set('Delta / braking / line: unavailable')
        for name,var in self.tires.values():var.set(f'{name}: temperature —; remaining —')
        self.render_history()
    def voice_changed(self):self.runtime.voice=self.voice.get()
    def use_simulation(self):self.runtime.use_simulation();self.reset()
    def load_reference(self):
        path=filedialog.askopenfilename(filetypes=[('Reference telemetry','*.json')])
        if not path:return
        try:
            import json
            from pathlib import Path
            from motorsport.recorded import Recording
            payload=json.loads(Path(path).read_text(encoding='utf-8-sig'));self.runtime.set_reference(Recording(payload['samples'],payload.get('provenance')));self.reset();self.latest.set('Reference loaded. Comparisons require an overlapping recorded run.')
        except Exception as exc:messagebox.showerror('Reference unavailable',str(exc))
    def load(self):
        path=filedialog.askopenfilename(filetypes=[('Recorded telemetry','*.json')])
        if not path:return
        try:self.runtime.load_recording(path);self.reset();self.latest.set('Recorded lap loaded. Start to play its timestamps.')
        except Exception as exc:messagebox.showerror('Recording unavailable',str(exc))
    def render_history(self):
        self.radio_log.configure(state='normal');self.radio_log.delete('1.0','end');self.radio_log.insert('end','\n\n'.join(self.history));self.radio_log.see('end');self.radio_log.configure(state='disabled')
    def poll(self):
        import queue
        self.runtime.volume=self.volume.get();self.runtime.effects=self.effects.get();self.runtime.voice=self.voice.get()
        while True:
            try:g,kind,data=self.runtime.results.get_nowait()
            except queue.Empty:break
            if g!=self.runtime.generation:continue
            if kind=='frame':
                self.speed.set(f"{data['speed']:.0f} km/h");self.details.set(f"Gear {data['gear']} • Throttle {data['throttle']:.0f}% • Brake {data['brake']:.0f}%");self.corner.set(data['corner'])
                delta=data.get('lap_delta');braking=data.get('braking_offset_m');line=data.get('lateral_offset')
                self.guidance.set(f"Delta {delta:+.3f} s" if delta is not None else 'Delta unavailable')
                if braking is not None:self.guidance.set(self.guidance.get()+f" • Braking {abs(braking):.1f} m {'early' if braking<0 else 'late'}")
                if line is not None:self.guidance.set(self.guidance.get()+f" • Line {line:.1f} source units")
                for key,(name,var) in self.tires.items():
                    temp=data['tire_temps'].get(key);wear=data['tire_wear'].get(key)
                    var.set(f'{name}: {temp:.1f}°C; {wear:.1f}% remaining' if temp is not None and wear is not None else f'{name}: data unavailable')
            elif kind=='radio':
                line=f"{data['time']:.1f}s • {data['severity']} • {data['engine']}\n{data['text']}";self.latest.set(line);self.history.append(line);self.render_history()
            else:self.latest.set(data)
        mode='recorded' if self.runtime.recording else 'telemetry simulation'
        self.status.set(f"{'Playing' if self.runtime.playing else 'Paused'} • {mode} • {self.runtime.ai.engine} coaching")
        if not self.runtime.stop.is_set():self.root.after(100,self.poll)
    def close(self):self.runtime.close();self.root.destroy()
    def mainloop(self):self.root.mainloop()
if __name__=='__main__':RaceEngineerGUI().mainloop()
