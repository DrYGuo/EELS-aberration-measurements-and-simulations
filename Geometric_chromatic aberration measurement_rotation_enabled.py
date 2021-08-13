# Control CAperture and drift tube for EELS aberration measurement
# author: Yueming Guo
# Date of creation: June 22 2021

import numpy as np
import time
import scipy.optimize
import threading
import contextlib
import logging
import time
from nion.typeshed import Interactive_1_0 as Interactive
from nion.typeshed import API_1_0 as API
from nion.typeshed import UI_1_0 as UI


class Controls(object):
    """docstring for Controls"""
    def __init__(self,api,scan,autostem,camera,eels_camera,interactive):
        self.api = api
        self.scan = scan
        self.autostem = autostem
        self.camera = camera
        self.eels_camera=eels_camera
        self.interactive = interactive
       # The exact name of the controls need to be checked
        self.shift_x_control_name ='CapPure.a' #''CAperture.a' "PV2_1Da"   "CapPure.a" 'CshPure.a'
        self.shift_y_control_name ='CapPure.b'  #CAperture.b' #"PV2_1Db"    "CapPure.b" 'CshPure.b'
        
        self.num_frames=[]
        self.num_frames_acquired=0

        self.start_x = autostem.get_control_output(self.shift_x_control_name)
        self.start_y = autostem.get_control_output(self.shift_y_control_name)

        print('Start x: '+str(self.start_x)+', y: '+str(self.start_y))
       # control_values
        self.x_coord=[]  
        self.y_coord=[]

       # dimensions
        self.EELS_row=[]
        self.EELS_col=[]

       # datasets
        self.Rochi=[]
        self.EELS=[]
       #state
        self.state = True


    def list_coord(self,step=8e-3,max=24e-3): # the values of PV2 are in A (not mA) # the values of CAperture are in rad (not mrad) CapPure 10e-3,max=20e-3    for CshPure step=100e-9,max=200e-9
        step_num=int(max/step)
        self.x_coord=np.linspace(-max,max,int(2*step_num+1))+self.start_x
        self.y_coord=np.linspace(-max,max,int(2*step_num+1))+self.start_y
        self.num_frames=int(self.x_coord.shape[0]*self.y_coord.shape[0])
        print('The x_coord is')
        print(self.x_coord)
        print('The y_coord is')
        print(self.y_coord)
        print('num_frames')
        print(self.num_frames)


    def shift_control_to(self,Da,Db,delay_time_s=1.5,theta=np.pi/4+0.01448):
        # Check for sanity: Units are m
        if abs(Da)>1000e-3 or abs(Db)>3000e-3:
            print('Stage position out of range!')
            return
        else:
            try:
                DX=Da*np.cos(theta)-Db*np.sin(theta)
                DY=Da*np.sin(theta)+Db*np.cos(theta)
                self.autostem.set_control_output(self.shift_x_control_name,DX)
                self.autostem.set_control_output(self.shift_y_control_name,DY)
                time.sleep(delay_time_s)
            except TimeoutError as e:
                print('Error!:')
                print(e) 


    def grab_ronchi(self):
        ''' Grab a frame from the Ronchi camera and return it'''
        if self.camera.is_playing == False:
            self.camera.start_playing()
        frame = self.camera.grab_next_to_start()[0] #not recording
        # if frame is good (How do I check?)
        data = frame.data
        print('Data shape'+str(data.shape[0])+str(data.shape[1]))
        return data


    def grab_eels(self):
        if self.eels_camera.is_playing == False:
            self.eels_camera.start_playing()
        frame = self.eels_camera.grab_next_to_start()[0] #not recording
        # if frame is good (How do I check?)
        data = frame.data
        self.EELS_row=data.shape[0]
        self.EELS_col=data.shape[1]
        print('Data shape'+str(data.shape[0])+str(data.shape[1]))
        return data
        


            # autostem.set_control_output("PV2_1Da", i*step, options={'value_type': 'local'})
                # autostem.set_control_output("PV2_1Db", j*step, options={'value_type': 'local'})

 
    def make_ronchi_stack(self):
        # depends on grab_rochi() and shif_coord
        firstframe = self.grab_ronchi()
        print('Grabbing this many frames '+str(self.num_frames))
        self.Ronchi = np.zeros((firstframe.shape[0],firstframe.shape[1],self.num_frames), dtype = firstframe.dtype)
        print('My array is this big '+str(self.Ronchi.shape))
        count=0
        try:
            #for it in range(self.num_frames):
            for Xi in self.x_coord:
                for Yi in self.y_coord:

                    X=Xi
                    Y=Yi
                    print('count, '+str(count)+' CAperture.a='+str(X)+'CAperture.b'+str(Y))

                    if self.interactive.cancelled is True:
                       break
                #print(str(it)+": "+str(X)+','+str(Y))
                    self.shift_control_to(X,Y)
                    ronchi = self.grab_ronchi()
                    self.Ronchi[:,:,count] = ronchi
                    self.num_frames_acquired +=1
                    count+=1
        except Exception as e:
            print('Oh dear!'+str(e))
        finally:           
            print('Return to the start position')
            self.shift_control_to(self.start_x,self.start_y)        

    def make_eels_stack(self):
        # depends on grab_rochi() and shif_coord
        firstframe = self.grab_eels()
        print('Grabbing this many frames '+str(self.num_frames))
        self.EELS = np.zeros((firstframe.shape[0],firstframe.shape[1],self.num_frames), dtype = firstframe.dtype)
        print('My array is this big '+str(self.EELS.shape))
        count=0
        try:
            for Xi in self.x_coord:
                for Yi in self.y_coord:
                    X=Xi
                    Y=Yi
                    print('count, '+str(count)+' CAperture.a='+str(X)+' CAperture.b'+str(Y))

                    if self.interactive.cancelled is True:
                        break
                    self.shift_control_to(X,Y)
                    EELS = self.grab_eels()
                    self.EELS[:,:,count] = EELS
                    self.num_frames_acquired +=1
                    count+=1
        
        except Exception as e:
            print('Oh dear!'+str(e))
        finally:           
            print('Return to the start position')
            self.shift_control_to(self.start_x,self.start_y) 


# Inherit the Controls class and add a new method make_eels_stack_2
class Controls_E_added(Controls):
    def __init__(self,api,scan,autostem,camera,eels_camera,interactive):
        super().__init__(api,scan,autostem,camera,eels_camera,interactive)

        # add energy shift 
        self.shift_e_control_name='DriftTubeVolts' # There is another one called DriftTubeVolts.
        # initialize the value of the drift tube
        self.start_E = autostem.get_control_output(self.shift_e_control_name)
        self.E_coord=[]  
        self.EELS_2=[]
        # for testing 
        self.test_list=[]



    def list_energy(self,step=10e-3,max=20e-3):
        step_num=int(max/step)
        self.E_coord=np.linspace(-max,max,int(2*step_num+1))+self.start_E
        print('The list of energy shifts:')
        print(self.E_coord)
        self.num_frames=int(self.x_coord.shape[0]*self.y_coord.shape[0]*self.E_coord.shape[0])
        print('The number of frames:')
        print(self.num_frames)

    def shift_E_to(self,energy_shift,delay_time_s=1.5):
        # Check sanity:
        if abs(energy_shift)>2:
            print('energy shift is out of range!')
            return
        else:
            try:
                self.autostem.set_control_output(self.shift_e_control_name,energy_shift)
                time.sleep(delay_time_s)
            except TimeoutError as e:
                print('Error!:')
                print(e)

    def test_loop(self):
        count=0
        for En in self.E_coord:
            for Xi in self.x_coord:
                for Yj in self.y_coord:
                    
                    print('En'+str(En)+'i'+str(Xi)+'j'+str(Yj))
                    self.test_list[count]=count

                    count+=1


    def make_eels_stack_2(self):
        # depends on grab_rochi() and shif_coord
        firstframe = self.grab_eels()
        print('Grabbing this many frames '+str(self.num_frames))
        self.EELS = np.zeros((firstframe.shape[0],firstframe.shape[1],self.num_frames), dtype = firstframe.dtype)
        self.EELS_2=np.zeros((firstframe.shape[0],firstframe.shape[1],self.num_frames),dtype = firstframe.dtype)
        print('My array is this big '+str(self.EELS.shape))
        count=0
        try:
            #for n,En in enumerate(self.E_coord):
            for En in self.E_coord:
                self.shift_E_to(En)
                #for i,Xi in enumerate(self.x_coord):
                for Xi in self.x_coord:
                    #for j,Yj in enumerate(self.y_coord):
                    for Yj in self.y_coord:
                       X=Xi
                       Y=Yj
                       print('count, '+str(count)+' CAperture.a='+str(X)+' CAperture.b'+str(Y)+'driftube='+str(En))
                       if self.interactive.cancelled is True:
                          break
                       self.shift_control_to(X,Y)
                       EELS = self.grab_eels()
                       print('Good up to here')
                       #self.EELS_2[:,:,i,j,n] = EELS
                       self.EELS_2[:,:,count]=EELS
                       print("good up to here too")
                       self.num_frames_acquired +=1
                       count+=1

        except Exception as e:
            print('Oh dear!'+str(e))
        finally:           
            print('Return to the start position')
            self.shift_control_to(self.start_x,self.start_y) 
            self.shift_E_to(self.start_E)


# Inherit the Controls class and implement the through focal series
class Controls_df(Controls):
    def __init__(self,api,scan,autostem,camera,eels_camera,interactive):
        super().__init__(api,scan,autostem,camera,eels_camera,interactive)

        # add defocus change 
        self.shift_df_control_name='C10' # This should be the stage height Z
        # initialize the value of the defocus
        self.start_df = autostem.get_control_output(self.shift_df_control_name)
        self.df_coord=[]  
        self.EELS_3=[]

    def list_df(self,step=1e-6,max=5e-6):  # unit meter not nm
        step_num=int(max/step)
        self.df_coord=np.linspace(-max,max,int(2*step_num+1))+self.start_df
        print('The list of defoci:')
        self.num_frames=int(self.df_coord.shape[0])
        print(self.df_coord)


    def shift_df_to(self,df_shift,delay_time_s=3):
        # Check sanity:
        if abs(df_shift)>6e-6:
            print('defocus is out of range!')
            return
        else:
            try:
                self.autostem.set_control_output(self.shift_df_control_name,df_shift)
                time.sleep(delay_time_s)
            except TimeoutError as e:
                print('Error!:')
                print(e)


    def make_eels_stack_3(self):
        # depends on grab_rochi() and shif_coord
        firstframe = self.grab_eels()
        print('Grabbing this many frames '+str(self.num_frames))
        self.EELS_3=np.zeros((firstframe.shape[0],firstframe.shape[1],self.num_frames),dtype = firstframe.dtype)
        print('My array is this big '+str(self.EELS_3.shape))
        count=0
        try:
            for df in self.df_coord:
                self.shift_df_to(df)
                print('count, '+str(count)+'df='+str(df))
                if self.interactive.cancelled is True:
                   break
                EELS = self.grab_eels()
                print('Good up to here')
                self.EELS_3[:,:,count]=EELS
                print("good up to here too")
                self.num_frames_acquired +=1
                count+=1
        
        except Exception as e:
            print('Oh dear!'+str(e))
        finally:           
            print('Return to the start position')
            self.shift_df_to(self.start_df) 







def script_main(api_broker):  # it is required to put this main as a function


    # An interface to Nion Swift. To instantiate class nion.typeshed.API_1_0.API
    api = api_broker.get_api(version='~1.0')
    interactive = api_broker.get_interactive(version='~1.0')
    scan = api.get_hardware_source_by_id("superscan",'1')
    autostem = api.get_instrument_by_id("autostem_controller", "1")
    # camera = api.get_hardware_source_by_id("autotuning_camera", version="1.0")
    camera = api.get_hardware_source_by_id("autotuning_camera", version="1.0")
    eels_camera=api.get_hardware_source_by_id("eels_camera",version='1.0')

 
    if camera.is_playing==True:
        print('CCD camera is on')
    if eels_camera.is_playing==True:
        print('EELS camera is on')
        


    from nion.utils import Registry
    stem_controller = Registry.get_component("stem_controller")
    scan = stem_controller.scan_controller
    eels_camera = stem_controller.eels_camera


    # Record Rochi at varies control values
    is_confirmed = interactive.confirm_yes_no('Is the detector mode in CCD?')
    if is_confirmed:
        print('starting the script and collect Rochigram')
        #Instantiate the class object
        control=Controls(api,scan,autostem,camera,eels_camera,interactive)
        #excute the list_coord to generate the control values 
        control.list_coord()
        #excute grab_rochi to assign the attribute to the object
        control.grab_ronchi()
        # Acquire Rochi
        control.make_ronchi_stack()
        # Send stuff back to Swift
        Ronchi_data=api.library.create_data_item_from_data(control.Ronchi, title = 'Ronchi_data')
        api.application.document_windows[0].display_data_item(Ronchi_data)
        print('Rochi data is recorded')

    # Record 2D EELS at varies control values
    
    is_confirmed2 = interactive.confirm_yes_no('Is the detector mode in EELS now and is the slit in? Also, you do not want to measure chromatic aberration?')
    if is_confirmed2:
        print('starting to collect EELS')
        #Instantiate the class object
        control2=Controls(api,scan,autostem,camera,eels_camera,interactive)
        #excute the list_coord to generate the control values 
        control2.list_coord()
        #excute grab_eels to assign the attribute to the object
        control2.grab_eels()
        # Acquire eels_stack
        control2.make_eels_stack()
        # Send stuff back to Swift
        EELS_data=api.library.create_data_item_from_data(control2.EELS, title = 'EELS_data_3D')
        api.application.document_windows[0].display_data_item(EELS_data)
        print('EELS data is recorded')

    # Record 2D EELS at varies XY and E values
    is_confirmed3 = interactive.confirm_yes_no('Is the detector mode in EELS now and is the slit in? Also, you want to measure both chromatic and geometric aberration?')
    if is_confirmed3:
        print('starting to collect EELS')
        #Instantiate the class object
        control3=Controls_E_added(api,scan,autostem,camera,eels_camera,interactive)
        #excute the list_coord to generate the control values
        control3.list_coord()
        control3.list_energy()
        #excute grab_eels to assign the attribute to the object
        control3.grab_eels()
 
        control3.make_eels_stack_2()
        # Send stuff back to Swift
        EELS_data2=api.library.create_data_item_from_data(control3.EELS_2, title = 'EELS_data_5D')
        api.application.document_windows[0].display_data_item(EELS_data2)
        print('EELS data is recorded')

        
# Record 2D EELS at varies foci
    is_confirmed4 = interactive.confirm_yes_no('Is the detector mode in EELS now and is the slit in? You want to measure via through focal series?')
    if is_confirmed4:
        print('starting to collect EELS')
        #Instantiate the class object
        control4=Controls_df(api,scan,autostem,camera,eels_camera,interactive)
        #excute the list_coord to generate the control values
        control4.list_df()
        #excute grab_eels to assign the attribute to the object
        control4.grab_eels()

        control4.make_eels_stack_3()
        # Send stuff back to Swift
        EELS_data3=api.library.create_data_item_from_data(control4.EELS_3, title = 'EELS_data_thru_focal')
        api.application.document_windows[0].display_data_item(EELS_data3)
        print('EELS data is recorded')




