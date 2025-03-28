/******************************************************************************
*
* CAEN SpA - Front End Division
* Via Vetraia, 11 - 55049 - Viareggio ITALY
* +390594388398 - www.caen.it
*
***************************************************************************//**
* \note TERMS OF USE:
* This program is free software; you can redistribute it and/or modify it under
* the terms of the GNU General Public License as published by the Free Software
* Foundation. This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. The user relies on the
* software, documentation and results solely at his own risk.
*
*  Description:
*  -----------------------------------------------------------------------------
*  This is a demo program that can be used with any model of the CAEN's
*  digitizer family. The purpose of WaveDump is to configure the digitizer,
*  start the acquisition, read the data and write them into output files
*  and/or plot the waveforms using 'gnuplot' as an external plotting tool.
*  The configuration of the digitizer (registers setting) is done by means of
*  a configuration file that contains a list of parameters.
*  This program uses the CAENDigitizer library which is then based on the
*  CAENComm library for the access to the devices through any type of physical
*  channel (VME, Optical Link, USB, etc...). The CAENComm support the following
*  communication paths:
*  PCI => A2818 => OpticalLink => Digitizer (any type)
*  PCI => V2718 => VME => Digitizer (only VME models)
*  USB => Digitizer (only Desktop or NIM models)
*  USB => V1718 => VME => Digitizer (only VME models)
*  If you have want to sue a VME digitizer with a different VME controller
*  you must provide the functions of the CAENComm library.
*
*  -----------------------------------------------------------------------------
*  Syntax: WaveDump [ConfigFile]
*  Default config file is "WaveDumpConfig.txt"
******************************************************************************/

#define WaveDump_Release        "3.8.1"
#define WaveDump_Release_Date   "June 2017"
#define DBG_TIME

#include <CAENDigitizer.h>
#include "WaveDump.h"
#include "WDconfig.h"
#include "WDplot.h"
#include "fft.h"
#include "keyb.h"
#include "X742CorrectionRoutines.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

extern int dc_file[MAX_CH];
extern int thr_file[MAX_CH];
int cal_ok[MAX_CH] = { 0 };

int maxtrig_rdm;
int maxtrig_muon;
int totCounter_rdm;
int totCounter_muon;



void setRunFile(char *msg) {

    FILE *fptr;
    if((fptr = fopen("/var/webdcs/RUN/run_digitizer_daq", "w")) != NULL) {

        fputs(msg, fptr);
        
    }
    fclose(fptr);

    //printf("WRITE %s", msg);
    //fflush(stdout);
}

void readRunFile(char *runfile) {
  
    FILE *fptr;
    if((fptr = fopen("/var/webdcs/RUN/run_digitizer_daq", "r")) != NULL) {

        fscanf(fptr, "%s", runfile);
        //fgets (runfile, 100, fptr);
        
    }
    fclose(fptr);

    //printf("READ %s", runfile);
    //fflush(stdout);
}

void logEntry(char *var, char *logfile) {


    time_t timer;
    char buffer[26];
    struct tm* tm_info;
    char msg[1000];

    // Make time format
    time(&timer);
    tm_info = localtime(&timer);
    strftime(buffer, 26, "%Y-%m-%d.%H:%M:%S", tm_info);

    sprintf(msg, "%s.[%s] %s", buffer, "DIGITZER-DAQ", var);


    char cmd[1000];
	sprintf(cmd, "echo '%s' >> %s ", msg, logfile);
    system(cmd);
    
    
    printf("%s\n", msg);
    fflush(stdout);

}


/* Error messages */
typedef enum  {
    ERR_NONE= 0,
    ERR_CONF_FILE_NOT_FOUND,
    ERR_DGZ_OPEN,
    ERR_BOARD_INFO_READ,
    ERR_INVALID_BOARD_TYPE,
    ERR_DGZ_PROGRAM,
    ERR_MALLOC,
    ERR_RESTART,
    ERR_INTERRUPT,
    ERR_READOUT,
    ERR_EVENT_BUILD,
    ERR_HISTO_MALLOC,
    ERR_UNHANDLED_BOARD,
    ERR_OUTFILE_WRITE,
	ERR_OVERTEMP,

    ERR_DUMMY_LAST,
} ERROR_CODES;
static char ErrMsg[ERR_DUMMY_LAST][100] = {
    "No Error",                                         /* ERR_NONE */
    "Configuration File not found",                     /* ERR_CONF_FILE_NOT_FOUND */
    "Can't open the digitizer",                         /* ERR_DGZ_OPEN */
    "Can't read the Board Info",                        /* ERR_BOARD_INFO_READ */
    "Can't run WaveDump for this digitizer",            /* ERR_INVALID_BOARD_TYPE */
    "Can't program the digitizer",                      /* ERR_DGZ_PROGRAM */
    "Can't allocate the memory for the readout buffer", /* ERR_MALLOC */
    "Restarting Error",                                 /* ERR_RESTART */
    "Interrupt Error",                                  /* ERR_INTERRUPT */
    "Readout Error",                                    /* ERR_READOUT */
    "Event Build Error",                                /* ERR_EVENT_BUILD */
    "Can't allocate the memory fro the histograms",     /* ERR_HISTO_MALLOC */
    "Unhandled board type",                             /* ERR_UNHANDLED_BOARD */
    "Output file write error",                          /* ERR_OUTFILE_WRITE */
	"Over Temperature",									/* ERR_OVERTEMP */

};


#ifndef max
#define max(a,b)            (((a) > (b)) ? (a) : (b))
#endif

static CAEN_DGTZ_IRQMode_t INTERRUPT_MODE = CAEN_DGTZ_IRQ_MODE_ROAK;

/* ###########################################################################
*  Functions
*  ########################################################################### */
/*! \fn      static long get_time()
*   \brief   Get time in milliseconds
*
*   \return  time in msec
*/
static long get_time()
{
    long time_ms;
#ifdef WIN32
    struct _timeb timebuffer;
    _ftime( &timebuffer );
    time_ms = (long)timebuffer.time * 1000 + (long)timebuffer.millitm;
#else
    struct timeval t1;
    struct timezone tz;
    gettimeofday(&t1, &tz);
    time_ms = (t1.tv_sec) * 1000 + t1.tv_usec / 1000;
#endif
    return time_ms;
}


/*! \fn      int GetMoreBoardNumChannels(CAEN_DGTZ_BoardInfo_t BoardInfo,  WaveDumpConfig_t *WDcfg)
*   \brief   calculate num of channels, num of bit and sampl period according to the board type
*
*   \param   BoardInfo   Board Type
*   \param   WDcfg       pointer to the config. struct
*   \return  0 = Success; -1 = unknown board type
*/
int GetMoreBoardInfo(int handle, CAEN_DGTZ_BoardInfo_t BoardInfo, WaveDumpConfig_t *WDcfg)
{
    int ret;
    switch(BoardInfo.FamilyCode) {
        CAEN_DGTZ_DRS4Frequency_t freq;

    case CAEN_DGTZ_XX724_FAMILY_CODE:
    case CAEN_DGTZ_XX781_FAMILY_CODE:
    case CAEN_DGTZ_XX780_FAMILY_CODE:
        WDcfg->Nbit = 14; WDcfg->Ts = 10.0; break;
    case CAEN_DGTZ_XX720_FAMILY_CODE: WDcfg->Nbit = 12; WDcfg->Ts = 4.0;  break;
    case CAEN_DGTZ_XX721_FAMILY_CODE: WDcfg->Nbit =  8; WDcfg->Ts = 2.0;  break;
    case CAEN_DGTZ_XX731_FAMILY_CODE: WDcfg->Nbit =  8; WDcfg->Ts = 2.0;  break;
    case CAEN_DGTZ_XX751_FAMILY_CODE: WDcfg->Nbit = 10; WDcfg->Ts = 1.0;  break;
    case CAEN_DGTZ_XX761_FAMILY_CODE: WDcfg->Nbit = 10; WDcfg->Ts = 0.25;  break;
    case CAEN_DGTZ_XX740_FAMILY_CODE: WDcfg->Nbit = 12; WDcfg->Ts = 16.0; break;
    case CAEN_DGTZ_XX725_FAMILY_CODE: WDcfg->Nbit = 14; WDcfg->Ts = 4.0; break;
    case CAEN_DGTZ_XX730_FAMILY_CODE: WDcfg->Nbit = 14; WDcfg->Ts = 2.0; break;
    case CAEN_DGTZ_XX742_FAMILY_CODE: 
        WDcfg->Nbit = 12; 
        if ((ret = CAEN_DGTZ_GetDRS4SamplingFrequency(handle, &freq)) != CAEN_DGTZ_Success) return CAEN_DGTZ_CommError;
        switch (freq) {
        case CAEN_DGTZ_DRS4_1GHz:
            WDcfg->Ts = 1.0;
            break;
        case CAEN_DGTZ_DRS4_2_5GHz:
            WDcfg->Ts = (float)0.4;
            break;
        case CAEN_DGTZ_DRS4_5GHz:
            WDcfg->Ts = (float)0.2;
            break;
		case CAEN_DGTZ_DRS4_750MHz:
            WDcfg->Ts = (float)(1.0/750.0)*1000.0;
            break;
        }
        switch(BoardInfo.FormFactor) {
        case CAEN_DGTZ_VME64_FORM_FACTOR:
        case CAEN_DGTZ_VME64X_FORM_FACTOR:
            WDcfg->MaxGroupNumber = 4;
            break;
        case CAEN_DGTZ_DESKTOP_FORM_FACTOR:
        case CAEN_DGTZ_NIM_FORM_FACTOR:
        default:
            WDcfg->MaxGroupNumber = 2;
            break;
        }
        break;
    default: return -1;
    }
    if (((BoardInfo.FamilyCode == CAEN_DGTZ_XX751_FAMILY_CODE) ||
        (BoardInfo.FamilyCode == CAEN_DGTZ_XX731_FAMILY_CODE) ) && WDcfg->DesMode)
        WDcfg->Ts /= 2;

    switch(BoardInfo.FamilyCode) {
    case CAEN_DGTZ_XX724_FAMILY_CODE:
    case CAEN_DGTZ_XX781_FAMILY_CODE:
    case CAEN_DGTZ_XX780_FAMILY_CODE:
    case CAEN_DGTZ_XX720_FAMILY_CODE:
    case CAEN_DGTZ_XX721_FAMILY_CODE:
    case CAEN_DGTZ_XX751_FAMILY_CODE:
    case CAEN_DGTZ_XX761_FAMILY_CODE:
    case CAEN_DGTZ_XX731_FAMILY_CODE:
        switch(BoardInfo.FormFactor) {
        case CAEN_DGTZ_VME64_FORM_FACTOR:
        case CAEN_DGTZ_VME64X_FORM_FACTOR:
            WDcfg->Nch = 8;
            break;
        case CAEN_DGTZ_DESKTOP_FORM_FACTOR:
        case CAEN_DGTZ_NIM_FORM_FACTOR:
            WDcfg->Nch = 4;
            break;
        }
        break;
    case CAEN_DGTZ_XX725_FAMILY_CODE:
    case CAEN_DGTZ_XX730_FAMILY_CODE:
        switch(BoardInfo.FormFactor) {
        case CAEN_DGTZ_VME64_FORM_FACTOR:
        case CAEN_DGTZ_VME64X_FORM_FACTOR:
            WDcfg->Nch = 16;
            break;
        case CAEN_DGTZ_DESKTOP_FORM_FACTOR:
        case CAEN_DGTZ_NIM_FORM_FACTOR:
            WDcfg->Nch = 8;
            break;
        }
        break;
    case CAEN_DGTZ_XX740_FAMILY_CODE:
        switch( BoardInfo.FormFactor) {
        case CAEN_DGTZ_VME64_FORM_FACTOR:
        case CAEN_DGTZ_VME64X_FORM_FACTOR:
            WDcfg->Nch = 64;
            break;
        case CAEN_DGTZ_DESKTOP_FORM_FACTOR:
        case CAEN_DGTZ_NIM_FORM_FACTOR:
            WDcfg->Nch = 32;
            break;
        }
        break;
    case CAEN_DGTZ_XX742_FAMILY_CODE:
        switch( BoardInfo.FormFactor) {
        case CAEN_DGTZ_VME64_FORM_FACTOR:
        case CAEN_DGTZ_VME64X_FORM_FACTOR:
            WDcfg->Nch = 36;
            break;
        case CAEN_DGTZ_DESKTOP_FORM_FACTOR:
        case CAEN_DGTZ_NIM_FORM_FACTOR:
            WDcfg->Nch = 16;
            break;
        }
        break;
    default:
        return -1;
    }
    return 0;
}

/*! \fn      int WriteRegisterBitmask(int32_t handle, uint32_t address, uint32_t data, uint32_t mask)
*   \brief   writes 'data' on register at 'address' using 'mask' as bitmask
*
*   \param   handle :   Digitizer handle
*   \param   address:   Address of the Register to write
*   \param   data   :   Data to Write on the Register
*   \param   mask   :   Bitmask to use for data masking
*   \return  0 = Success; negative numbers are error codes
*/
int WriteRegisterBitmask(int32_t handle, uint32_t address, uint32_t data, uint32_t mask) {
    int32_t ret = CAEN_DGTZ_Success;
    uint32_t d32 = 0xFFFFFFFF;

    ret = CAEN_DGTZ_ReadRegister(handle, address, &d32);
    if(ret != CAEN_DGTZ_Success)
        return ret;

    data &= mask;
    d32 &= ~mask;
    d32 |= data;
    ret = CAEN_DGTZ_WriteRegister(handle, address, d32);
    return ret;
}

/*! \fn      int ProgramDigitizer(int handle, WaveDumpConfig_t WDcfg)
*   \brief   configure the digitizer according to the parameters read from
*            the cofiguration file and saved in the WDcfg data structure
*
*   \param   handle   Digitizer handle
*   \param   WDcfg:   WaveDumpConfig data structure
*   \return  0 = Success; negative numbers are error codes
*/
int ProgramDigitizer(int handle, WaveDumpConfig_t WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo)
{
    int i, j, ret = 0;

    /* reset the digitizer */
    ret |= CAEN_DGTZ_Reset(handle);
    if (ret != 0) {
        printf("Error: Unable to reset digitizer.\nPlease reset digitizer manually then restart the program\n");
        return -1;
    }

    // Set the waveform test bit for debugging
    if (WDcfg.TestPattern)
        ret |= CAEN_DGTZ_WriteRegister(handle, CAEN_DGTZ_BROAD_CH_CONFIGBIT_SET_ADD, 1<<3);
    // custom setting for X742 boards
    if (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) {
        ret |= CAEN_DGTZ_SetFastTriggerDigitizing(handle,WDcfg.FastTriggerEnabled);
        ret |= CAEN_DGTZ_SetFastTriggerMode(handle,WDcfg.FastTriggerMode);
    }
    if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX751_FAMILY_CODE) || (BoardInfo.FamilyCode == CAEN_DGTZ_XX731_FAMILY_CODE)) {
        ret |= CAEN_DGTZ_SetDESMode(handle, WDcfg.DesMode);
    }
    ret |= CAEN_DGTZ_SetRecordLength(handle, WDcfg.RecordLength);
    ret |= CAEN_DGTZ_GetRecordLength(handle, &WDcfg.RecordLength);

    if (BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE) {
        ret |= CAEN_DGTZ_SetDecimationFactor(handle, WDcfg.DecimationFactor);
    }

    ret |= CAEN_DGTZ_SetPostTriggerSize(handle, WDcfg.PostTrigger);
    if(BoardInfo.FamilyCode != CAEN_DGTZ_XX742_FAMILY_CODE) {
        uint32_t pt;
        ret |= CAEN_DGTZ_GetPostTriggerSize(handle, &pt);
        WDcfg.PostTrigger = pt;
    }
    ret |= CAEN_DGTZ_SetIOLevel(handle, WDcfg.FPIOtype);
    if( WDcfg.InterruptNumEvents > 0) {
        // Interrupt handling
        if( ret |= CAEN_DGTZ_SetInterruptConfig( handle, CAEN_DGTZ_ENABLE,
            VME_INTERRUPT_LEVEL, VME_INTERRUPT_STATUS_ID,
            (uint16_t)WDcfg.InterruptNumEvents, INTERRUPT_MODE)!= CAEN_DGTZ_Success) {
                printf( "\nError configuring interrupts. Interrupts disabled\n\n");
                WDcfg.InterruptNumEvents = 0;
        }
    }
	
    ret |= CAEN_DGTZ_SetMaxNumEventsBLT(handle, WDcfg.NumEvents);
    ret |= CAEN_DGTZ_SetAcquisitionMode(handle, CAEN_DGTZ_SW_CONTROLLED);
    ret |= CAEN_DGTZ_SetExtTriggerInputMode(handle, WDcfg.ExtTriggerMode);

    if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE) || (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE)){
        ret |= CAEN_DGTZ_SetGroupEnableMask(handle, WDcfg.EnableMask);
        for(i=0; i<(WDcfg.Nch/8); i++) {
            if (WDcfg.EnableMask & (1<<i)) {
                if (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) {
                    for(j=0; j<8; j++) {
                        if (WDcfg.DCoffsetGrpCh[i][j] != -1)
                            ret |= CAEN_DGTZ_SetChannelDCOffset(handle,(i*8)+j, WDcfg.DCoffsetGrpCh[i][j]);
						else
                            ret |= CAEN_DGTZ_SetChannelDCOffset(handle, (i * 8) + j, WDcfg.DCoffset[i]);

                    }
                }
                else {
                    ret |= CAEN_DGTZ_SetGroupDCOffset(handle, i, WDcfg.DCoffset[i]);
                    ret |= CAEN_DGTZ_SetGroupSelfTrigger(handle, WDcfg.ChannelTriggerMode[i], (1<<i));
                    ret |= CAEN_DGTZ_SetGroupTriggerThreshold(handle, i, WDcfg.Threshold[i]);
                    ret |= CAEN_DGTZ_SetChannelGroupMask(handle, i, WDcfg.GroupTrgEnableMask[i]);
                } 
                ret |= CAEN_DGTZ_SetTriggerPolarity(handle, i, WDcfg.PulsePolarity[i]); //.TriggerEdge
            }
        }
    } else {
        ret |= CAEN_DGTZ_SetChannelEnableMask(handle, WDcfg.EnableMask);
        for (i = 0; i < WDcfg.Nch; i++) {
            if (WDcfg.EnableMask & (1<<i)) {
                ret |= CAEN_DGTZ_SetChannelDCOffset(handle, i, WDcfg.DCoffset[i]);
                if (BoardInfo.FamilyCode != CAEN_DGTZ_XX730_FAMILY_CODE &&
                    BoardInfo.FamilyCode != CAEN_DGTZ_XX725_FAMILY_CODE)
                    ret |= CAEN_DGTZ_SetChannelSelfTrigger(handle, WDcfg.ChannelTriggerMode[i], (1<<i));
                ret |= CAEN_DGTZ_SetChannelTriggerThreshold(handle, i, WDcfg.Threshold[i]);
                ret |= CAEN_DGTZ_SetTriggerPolarity(handle, i, WDcfg.PulsePolarity[i]); //.TriggerEdge
            }
        }
        if (BoardInfo.FamilyCode == CAEN_DGTZ_XX730_FAMILY_CODE ||
            BoardInfo.FamilyCode == CAEN_DGTZ_XX725_FAMILY_CODE) {
            // channel pair settings for x730 boards
            for (i = 0; i < WDcfg.Nch; i += 2) {
                if (WDcfg.EnableMask & (0x3 << i)) {
                    CAEN_DGTZ_TriggerMode_t mode = WDcfg.ChannelTriggerMode[i];
                    uint32_t pair_chmask = 0;

                    // Build mode and relevant channelmask. The behaviour is that,
                    // if the triggermode of one channel of the pair is DISABLED,
                    // this channel doesn't take part to the trigger generation.
                    // Otherwise, if both are different from DISABLED, the one of
                    // the even channel is used.
                    if (WDcfg.ChannelTriggerMode[i] != CAEN_DGTZ_TRGMODE_DISABLED) {
                        if (WDcfg.ChannelTriggerMode[i + 1] == CAEN_DGTZ_TRGMODE_DISABLED)
                            pair_chmask = (0x1 << i);
                        else
                            pair_chmask = (0x3 << i);
                    }
                    else {
                        mode = WDcfg.ChannelTriggerMode[i + 1];
                        pair_chmask = (0x2 << i);
                    }

                    pair_chmask &= WDcfg.EnableMask;
                    ret |= CAEN_DGTZ_SetChannelSelfTrigger(handle, mode, pair_chmask);
                }
            }
        }
    }
    if (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) {
        for(i=0; i<(WDcfg.Nch/8); i++) {
            ret |= CAEN_DGTZ_SetDRS4SamplingFrequency(handle, WDcfg.DRS4Frequency);
            ret |= CAEN_DGTZ_SetGroupFastTriggerDCOffset(handle,i,WDcfg.FTDCoffset[i]);
            ret |= CAEN_DGTZ_SetGroupFastTriggerThreshold(handle,i,WDcfg.FTThreshold[i]);
        }
    }

    /* execute generic write commands */
    for(i=0; i<WDcfg.GWn; i++)
        ret |= WriteRegisterBitmask(handle, WDcfg.GWaddr[i], WDcfg.GWdata[i], WDcfg.GWmask[i]);

    if (ret)
        printf("Warning: errors found during the programming of the digitizer.\nSome settings may not be executed\n");

    return 0;
}

/*! \fn      void GoToNextEnabledGroup(WaveDumpRun_t *WDrun, WaveDumpConfig_t *WDcfg)
*   \brief   selects the next enabled group for plotting
*
*   \param   WDrun:   Pointer to the WaveDumpRun_t data structure
*   \param   WDcfg:   Pointer to the WaveDumpConfig_t data structure
*/
void GoToNextEnabledGroup(WaveDumpRun_t *WDrun, WaveDumpConfig_t *WDcfg) {
    if ((WDcfg->EnableMask) && (WDcfg->Nch>8)) {
        int orgPlotIndex = WDrun->GroupPlotIndex;
        do {
            WDrun->GroupPlotIndex = (++WDrun->GroupPlotIndex)%(WDcfg->Nch/8);
        } while( !((1 << WDrun->GroupPlotIndex)& WDcfg->EnableMask));
        if( WDrun->GroupPlotIndex != orgPlotIndex) {
            printf("Plot group set to %d\n", WDrun->GroupPlotIndex);
        }
    }
    ClearPlot();
}

/*! \brief   return TRUE if board descriped by 'BoardInfo' supports
*            calibration or not.
*
*   \param   BoardInfo board descriptor
*/
int32_t BoardSupportsCalibration(CAEN_DGTZ_BoardInfo_t BoardInfo) {
    return
		BoardInfo.FamilyCode == CAEN_DGTZ_XX761_FAMILY_CODE ||
        BoardInfo.FamilyCode == CAEN_DGTZ_XX751_FAMILY_CODE ||
        BoardInfo.FamilyCode == CAEN_DGTZ_XX730_FAMILY_CODE ||
        BoardInfo.FamilyCode == CAEN_DGTZ_XX725_FAMILY_CODE;
}

/*! \brief   return TRUE if board descriped by 'BoardInfo' supports
*            temperature read or not.
*
*   \param   BoardInfo board descriptor
*/
int32_t BoardSupportsTemperatureRead(CAEN_DGTZ_BoardInfo_t BoardInfo) {
    return
        BoardInfo.FamilyCode == CAEN_DGTZ_XX751_FAMILY_CODE ||
        BoardInfo.FamilyCode == CAEN_DGTZ_XX730_FAMILY_CODE ||
        BoardInfo.FamilyCode == CAEN_DGTZ_XX725_FAMILY_CODE;
}

/*! \brief   Write the event data on x742 boards into the output files
*
*   \param   WDrun Pointer to the WaveDumpRun data structure
*   \param   WDcfg Pointer to the WaveDumpConfig data structure
*   \param   EventInfo Pointer to the EventInfo data structure
*   \param   Event Pointer to the Event to write
*/
void calibrate(int handle, WaveDumpRun_t *WDrun, CAEN_DGTZ_BoardInfo_t BoardInfo) {
    printf("\n");
    if (BoardSupportsCalibration(BoardInfo)) {
        if (WDrun->AcqRun == 0) {
            int32_t ret = CAEN_DGTZ_Calibrate(handle);
            if (ret == CAEN_DGTZ_Success) {
                printf("ADC Calibration successfully executed.\n");
            }
            else {
                printf("ADC Calibration failed. CAENDigitizer ERR %d\n", ret);
            }
            printf("\n");
        }
        else {
            printf("Can't run ADC calibration while acquisition is running.\n");
        }
    }
    else {
        printf("ADC Calibration not needed for this board family.\n");
    }
}


/*! \fn      void Calibrate_XX740_DC_Offset(int handle, WaveDumpConfig_t WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo)
*   \brief   calibrates DAC of enabled channel groups (only if BASELINE_SHIFT is in use)
*
*   \param   handle   Digitizer handle
*   \param   WDcfg:   Pointer to the WaveDumpConfig_t data structure
*   \param   BoardInfo: structure with the board info
*/
void Calibrate_XX740_DC_Offset(int handle, WaveDumpConfig_t WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo)
{
	float cal = 1;
	float offset = 0;
	int i = 0, acq = 0, k = 0, p=0;
CAEN_DGTZ_ErrorCode ret;
CAEN_DGTZ_AcqMode_t mem_mode;
uint32_t  AllocatedSize;

ERROR_CODES ErrCode = ERR_NONE;
uint32_t BufferSize;
CAEN_DGTZ_EventInfo_t       EventInfo;
char *buffer = NULL;
char *EventPtr = NULL;
CAEN_DGTZ_UINT16_EVENT_t    *Event16 = NULL;

ret = CAEN_DGTZ_GetAcquisitionMode(handle, &mem_mode);//chosen value stored
if (ret)
printf("Error trying to read acq mode!!\n");
ret = CAEN_DGTZ_SetAcquisitionMode(handle, CAEN_DGTZ_SW_CONTROLLED);
if (ret)
printf("Error trying to set acq mode!!\n");
ret = CAEN_DGTZ_SetExtTriggerInputMode(handle, CAEN_DGTZ_TRGMODE_DISABLED);
if (ret)
printf("Error trying to set ext trigger!!\n");
ret = CAEN_DGTZ_SetPostTriggerSize(handle, 0);
if (ret)
printf("Error trying to set post trigger!!\n");
///malloc
ret = CAEN_DGTZ_MallocReadoutBuffer(handle, &buffer, &AllocatedSize);
if (ret) {
	ErrCode = ERR_MALLOC;
	goto QuitProgram;
}

	ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event16);

if (ret != CAEN_DGTZ_Success) {
	ErrCode = ERR_MALLOC;
	goto QuitProgram;
}



uint32_t dc[NPOINTS] = {25,75}; //test values (%)

	for (i = 0; i < (WDcfg.Nch / 8); i++)
		{
		 float avg_value[NPOINTS] = { 0 };
			if (WDcfg.EnableMask & (1 << i) && WDcfg.Version_used[i] == 1)
			{	
				printf("Group %d DAC calibration...\n", i);
				ret = CAEN_DGTZ_SetGroupSelfTrigger(handle, CAEN_DGTZ_TRGMODE_DISABLED, (1 << i));
				if (ret)
					printf("Warning: error disabling group %d self trigger\n", i);

				ret = CAEN_DGTZ_SWStartAcquisition(handle);
				if (ret)
				{
					printf("Warning: error starting X740 acq\n");
					goto QuitProgram;
				}

			cal_ok[i] = Calibration_is_possible(handle, i, WDcfg, BoardInfo);
			if (cal_ok[i])
			{
				for (p = 0; p < NPOINTS; p++)
				{

					ret = CAEN_DGTZ_SetGroupDCOffset(handle, (uint32_t)i, (uint32_t)((float)(abs(dc[p] - 100))*(655.35)));
					if (ret)
						printf("Warning: error setting group %d test offset\n", i);
#ifdef _WIN32
					Sleep(200);
#else
					usleep(200000);
#endif

					int value[NACQS] = { 0 };
					for (acq = 0; acq < NACQS; acq++)
					{
						CAEN_DGTZ_SendSWtrigger(handle);

						ret = CAEN_DGTZ_ReadData(handle, CAEN_DGTZ_SLAVE_TERMINATED_READOUT_MBLT, buffer, &BufferSize);
						if (ret) {
							ErrCode = ERR_READOUT;
							goto QuitProgram;
						}

						ret = CAEN_DGTZ_GetEventInfo(handle, buffer, BufferSize, 0, &EventInfo, &EventPtr);
						if (ret) {
							ErrCode = ERR_EVENT_BUILD;
							goto QuitProgram;
						}
						// decode the event //
						ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event16);


						if (ret) {
							ErrCode = ERR_EVENT_BUILD;
							goto QuitProgram;
						}


						for (k = 1; k < 7; k++) //mean over 6 samples
							value[acq] += (int)(Event16->DataChannel[i * 8][k]);

						value[acq] = (value[acq] / 6);

					}//for acq
					 ///check for clean baselines
					int max = 0;
					int mpp = 0;
					int size = (int)pow(2, (double)BoardInfo.ADC_NBits);
					int *freq = calloc(size, sizeof(int));

					for (k = 0; k < NACQS; k++)
					{
						if (value[k] > 0 && value[k] < size)
						{
							freq[value[k]]++;
							if (freq[value[k]] > max) { max = freq[value[k]]; mpp = value[k]; }
						}
					}

					free(freq);
					int ok = 0;
					for (k = 0; k < NACQS; k++)
					{
						if (value[k] == mpp || value[k] == (mpp + 1) || value[k] == (mpp - 1))
						{
							avg_value[p] = avg_value[p] + (float)value[k]; ok++;
						}
					}
					avg_value[p] = (avg_value[p] / (float)ok)*100. / (float)size;
				}// for p
				cal = ((float)(avg_value[1] - avg_value[0]) / (float)(dc[1] - dc[0]));
				offset = (float)(dc[1] * avg_value[0] - dc[0] * avg_value[1]) / (float)(dc[1] - dc[0]);
				//printf("Cal %f   offset %f\n", cal, offset);
			}///close if cal ok

				if (WDcfg.PulsePolarity[i] == CAEN_DGTZ_PulsePolarityPositive)
				{
					WDcfg.DCoffset[i] = (uint32_t)((float)(fabs(((float)dc_file[i] - offset) / cal - 100.))*(655.35));
					if (WDcfg.DCoffset[i] > 65535) WDcfg.DCoffset[i] = 65535;
					if (WDcfg.DCoffset[i] < 0) WDcfg.DCoffset[i] = 0;
				}
				else
					if (WDcfg.PulsePolarity[i] == CAEN_DGTZ_PulsePolarityNegative)
					{
						WDcfg.DCoffset[i] = (uint32_t)((float)(fabs(((fabs(dc_file[i] - 100.) - offset) / cal) - 100.))*(655.35));
						if (WDcfg.DCoffset[i] < 0) WDcfg.DCoffset[i] = 0;
						if (WDcfg.DCoffset[i] > 65535) WDcfg.DCoffset[i] = 65535;

					}

				ret = CAEN_DGTZ_SetGroupDCOffset(handle, (uint32_t)i, WDcfg.DCoffset[i]);
				if (ret)
					printf("Warning: error setting group %d calibrated offset\n", i);
#ifdef _WIN32
				Sleep(200);
#else
				usleep(200000);
#endif
			}
		}
		//printf("DAC Calibration ready\n");

		CAEN_DGTZ_SWStopAcquisition(handle);

		///free events e buffer
		CAEN_DGTZ_FreeReadoutBuffer(&buffer);

		CAEN_DGTZ_FreeEvent(handle, (void**)&Event16);

		Set_correct_XX740_Threshold(handle, WDcfg, BoardInfo);

		ret |= CAEN_DGTZ_SetPostTriggerSize(handle, WDcfg.PostTrigger);
		ret |= CAEN_DGTZ_SetAcquisitionMode(handle, mem_mode);
		ret |= CAEN_DGTZ_SetExtTriggerInputMode(handle, WDcfg.ExtTriggerMode);
		if (ret)
			printf("Warning: error setting recorded parameters\n");

	QuitProgram:
		if (ErrCode) {
			printf("\a%s\n", ErrMsg[ErrCode]);
#ifdef WIN32
			printf("Press a key to quit\n");
			getch();
#endif
		}
}


/*! \fn      void Set_correct_XX740_Threshold(int handle, WaveDumpConfig_t WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo)
*   \brief   sets the trigger threshold relative to the baseline for models X740 (only if BASELINE_SHIFT is in use)
*
*   \param   handle   Digitizer handle
*   \param   WDcfg:   Pointer to the WaveDumpConfig_t data structure
*   \param   BoardInfo: structure with the board info
*/
void Set_correct_XX740_Threshold(int handle, WaveDumpConfig_t WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo)
{
	int i = 0,  k=0;
	CAEN_DGTZ_ErrorCode ret;
	uint32_t  AllocatedSize;

	ERROR_CODES ErrCode = ERR_NONE;
	uint32_t BufferSize;
	CAEN_DGTZ_EventInfo_t       EventInfo;
	char *buffer = NULL;
	char *EventPtr = NULL;
	CAEN_DGTZ_UINT16_EVENT_t    *Event16 = NULL;

	///malloc
	ret = CAEN_DGTZ_MallocReadoutBuffer(handle, &buffer, &AllocatedSize);
	if (ret) {
		ErrCode = ERR_MALLOC;
		goto QuitProgram;
	}

		ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event16);
	
	if (ret != CAEN_DGTZ_Success) {
		ErrCode = ERR_MALLOC;
		goto QuitProgram;
	}

	//uint32_t mask;
//	CAEN_DGTZ_GetChannelEnableMask(handle, &mask);

	CAEN_DGTZ_SWStartAcquisition(handle);
	for ( i = 0; i < (WDcfg.Nch / 8); i++)
	{

		if (WDcfg.EnableMask & (1 << i) && WDcfg.Version_used[i] == 1)
		{
		 if (cal_ok[i])
		  {
			int baseline = 0;
			CAEN_DGTZ_SendSWtrigger(handle);

			ret = CAEN_DGTZ_ReadData(handle, CAEN_DGTZ_SLAVE_TERMINATED_READOUT_MBLT, buffer, &BufferSize);
			if (ret) {
				ErrCode = ERR_READOUT;
				goto QuitProgram;
			}

			ret = CAEN_DGTZ_GetEventInfo(handle, buffer, BufferSize, 0, &EventInfo, &EventPtr);
			if (ret) {
				ErrCode = ERR_EVENT_BUILD;
				goto QuitProgram;
			}

				ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event16);

			if (ret) {
				ErrCode = ERR_EVENT_BUILD;
				goto QuitProgram;
			}


			for (k = 1; k < 11; k++) //mean over 10 samples
					baseline += (int)(Event16->DataChannel[i*8][k]);

	
			baseline = (baseline / 10);

			if (WDcfg.PulsePolarity[i] == CAEN_DGTZ_PulsePolarityPositive)
				WDcfg.Threshold[i] = (uint32_t)baseline + thr_file[i];
			else 	if (WDcfg.PulsePolarity[i] == CAEN_DGTZ_PulsePolarityNegative)
				WDcfg.Threshold[i] = (uint32_t)baseline - thr_file[i];

			if (WDcfg.Threshold[i] < 0) WDcfg.Threshold[i] = 0;
			int size = (int)pow(2, (double)BoardInfo.ADC_NBits);
			if (WDcfg.Threshold[i] > (uint32_t)size) WDcfg.Threshold[i] = size;
		 }//if cal ok i
		 else
			 WDcfg.Threshold[i] = thr_file[i];

			ret = CAEN_DGTZ_SetGroupTriggerThreshold(handle, i, WDcfg.Threshold[i]);
			if (ret)
				printf("Warning: error setting ch %d corrected threshold\n", i);

			ret |= CAEN_DGTZ_SetGroupSelfTrigger(handle, WDcfg.ChannelTriggerMode[i], (1 << i));
			ret |= CAEN_DGTZ_SetTriggerPolarity(handle, i, WDcfg.PulsePolarity[i]); //.TriggerEdge
			ret |= CAEN_DGTZ_SetChannelGroupMask(handle, i, WDcfg.GroupTrgEnableMask[i]);
		}

	}
	CAEN_DGTZ_SWStopAcquisition(handle);

	CAEN_DGTZ_FreeReadoutBuffer(&buffer);

	CAEN_DGTZ_FreeEvent(handle, (void**)&Event16);


QuitProgram:
	if (ErrCode) {
		printf("\a%s\n", ErrMsg[ErrCode]);
#ifdef WIN32
		printf("Press a key to quit\n");
		getch();
#endif
	}
}

int Calibration_is_possible(int handle, int ch, WaveDumpConfig_t WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo)
{
	int res;
	int i = 0;
	CAEN_DGTZ_ErrorCode ret;
	uint32_t  AllocatedSize;

	ERROR_CODES ErrCode = ERR_NONE;
	uint32_t BufferSize;
	CAEN_DGTZ_EventInfo_t       EventInfo;
	char *buffer = NULL;
	char *EventPtr = NULL;
	CAEN_DGTZ_UINT16_EVENT_t    *Event16 = NULL;
	CAEN_DGTZ_UINT8_EVENT_t     *Event8 = NULL;

	///malloc
	ret = CAEN_DGTZ_MallocReadoutBuffer(handle, &buffer, &AllocatedSize);
	if (ret) {
		ErrCode = ERR_MALLOC;
		goto QuitProgram;
	}

	if (WDcfg.Nbit == 8)
		ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event8);
	else {
		ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event16);
	}
	if (ret != CAEN_DGTZ_Success) {
		ErrCode = ERR_MALLOC;
		goto QuitProgram;
	}

	int freq_max = 0;
	int freq_min = 0;
	int freq_bl = 0;
	int real_bl;
	int max = 0, min = 10000000;
	int pmax = 0,pmin=0;
	uint32_t dc_test = 32767; //test value

	int size = (int)pow(2, (double)BoardInfo.ADC_NBits);
	float expected_bl = 0.5*(float)size;

	if((BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE))
    ret = CAEN_DGTZ_SetGroupDCOffset(handle, (uint32_t)ch, (uint32_t)(dc_test));
	else
	ret = CAEN_DGTZ_SetChannelDCOffset(handle, (uint32_t)ch, (uint32_t)(dc_test));
	if (ret)
		printf("Warning: error setting ch %d test offset\n", ch);

#ifdef _WIN32
	Sleep(500);
#else
	usleep(500000);
#endif

	CAEN_DGTZ_SendSWtrigger(handle);

	ret = CAEN_DGTZ_ReadData(handle, CAEN_DGTZ_SLAVE_TERMINATED_READOUT_MBLT, buffer, &BufferSize);
	if (ret) {
		ErrCode = ERR_READOUT;
		goto QuitProgram;
	}

	ret = CAEN_DGTZ_GetEventInfo(handle, buffer, BufferSize, 0, &EventInfo, &EventPtr);
	if (ret) {
		ErrCode = ERR_EVENT_BUILD;
		goto QuitProgram;
	}
	// decode the event //
	if (WDcfg.Nbit == 8)
		ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event8);
	else
		ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event16);

	if (ret) {
		ErrCode = ERR_EVENT_BUILD;
		goto QuitProgram;
	}

	int *value = calloc(WDcfg.RecordLength, sizeof(int));
	for (i = 2; i < (WDcfg.RecordLength-2); i++) //scan all samples, look for max and min
	{
		if (WDcfg.Nbit == 8)
			value[i] = (int)(Event8->DataChannel[ch][i]);
		else
		{
			if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE))
				value[i] = (int)(Event16->DataChannel[ch * 8][i]);
			else
				value[i] = (int)(Event16->DataChannel[ch][i]);
		}

		if (value[i] > max && value[i] <(size-10)) { max = value[i]; pmax = i; }
		if (value[i] < min && value[i]>10) {min = value[i]; pmin = i;	}

	}//close for i/
	for (i = 2; i < (WDcfg.RecordLength-2); i++) //scan all samples
	{
		if (value[i]>(min - 10) && value[i]<(min + 10)) freq_min++;
		if (value[i]>(max - 10) && value[i]<(max + 10)) freq_max++;
	}

	free(value);
	if (WDcfg.PulsePolarity[ch] == CAEN_DGTZ_PulsePolarityPositive) {freq_bl = freq_min; real_bl = min;}
	else
	if (WDcfg.PulsePolarity[ch] == CAEN_DGTZ_PulsePolarityNegative) {freq_bl = freq_max; real_bl = max;}

	///printf("  CH %d:  expected bl %f, real bl %d, freq_bl %d, min  %d in pos %d, max  %d in pos %d\n",ch, expected_bl, real_bl,freq_bl, min,pmin, max,pmax);
	if (freq_bl<(WDcfg.RecordLength*0.6) || fabs((float)real_bl-(float)expected_bl)/expected_bl>0.25)
	{
		if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE))
		printf("DAC calibration failed for group %d.\n The group trigger threshold will be absolute.\n Disconnect the input signal from channel %d and restart acquisition to calibrate.\n", ch,(ch*8));
		else
		printf("DAC calibration failed for channel %d.\n The channel trigger threshold will be absolute.\n Disconnect the input signal and restart acquisition to calibrate.\n",ch);
		res = 0;
#ifdef _WIN32
		Sleep(500);
#else
		usleep(500000);
#endif
	}
	else res = 1;

	///free events e buffer
	CAEN_DGTZ_FreeReadoutBuffer(&buffer);
	if (WDcfg.Nbit == 8)
		CAEN_DGTZ_FreeEvent(handle, (void**)&Event8);
	else
		CAEN_DGTZ_FreeEvent(handle, (void**)&Event16);

	return res;

QuitProgram:
	if (ErrCode) {
		printf("\a%s\n", ErrMsg[ErrCode]);
#ifdef WIN32
		printf("Press a key to quit\n");
		getch();
#endif
	}
}



/*! \fn      void Calibrate_DC_Offset(int handle, WaveDumpConfig_t WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo)
*   \brief   calibrates DAC of enabled channels (only if BASELINE_SHIFT is in use)
*
*   \param   handle   Digitizer handle
*   \param   WDcfg:   Pointer to the WaveDumpConfig_t data structure
*   \param   BoardInfo: structure with the board info
*/
void Calibrate_DC_Offset(int handle, WaveDumpConfig_t WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo) 
{
	float cal = 1;
	float offset = 0;
	int i = 0, k = 0, p = 0, acq = 0, ch=0;
	CAEN_DGTZ_ErrorCode ret;
	CAEN_DGTZ_AcqMode_t mem_mode;
	uint32_t  AllocatedSize;

	ERROR_CODES ErrCode = ERR_NONE;
	uint32_t BufferSize;
	CAEN_DGTZ_EventInfo_t       EventInfo;
	char *buffer = NULL;
	char *EventPtr = NULL;
	CAEN_DGTZ_UINT16_EVENT_t    *Event16 = NULL;
	CAEN_DGTZ_UINT8_EVENT_t     *Event8 = NULL;

	ret = CAEN_DGTZ_GetAcquisitionMode(handle, &mem_mode);//chosen value stored
	if (ret)
		printf("Error trying to read acq mode!!\n");
	ret = CAEN_DGTZ_SetAcquisitionMode(handle, CAEN_DGTZ_SW_CONTROLLED);
	if (ret)
		printf("Error trying to set acq mode!!\n");
	ret = CAEN_DGTZ_SetExtTriggerInputMode(handle, CAEN_DGTZ_TRGMODE_DISABLED);
	if (ret)
		printf("Error trying to set ext trigger!!\n");
	ret = CAEN_DGTZ_SetPostTriggerSize(handle, 0);
	if (ret)
		printf("Error trying to set post trigger!!\n");
	///malloc
	ret = CAEN_DGTZ_MallocReadoutBuffer(handle, &buffer, &AllocatedSize);
	if (ret) {
		ErrCode = ERR_MALLOC;
		goto QuitProgram;
	}

	if (WDcfg.Nbit == 8)
		ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event8);
	else {
			ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event16);		
	}
	if (ret != CAEN_DGTZ_Success) {
		ErrCode = ERR_MALLOC;
		goto QuitProgram;
	}

	ret = CAEN_DGTZ_SWStartAcquisition(handle);
	if (ret)
	{
		printf("Warning: error starting acq\n");
		goto QuitProgram;
	}

	float avg_value[NPOINTS] = { 0 };
	
	uint32_t dc[NPOINTS] = {25,75}; //test values (%)

	for (ch = 0; ch < (int32_t)BoardInfo.Channels; ch++)
	{
		if (WDcfg.EnableMask & (1 << ch) && WDcfg.Version_used[ch] ==1)
		{

			printf("Starting channel %d DAC calibration...\n", ch);
			ret = CAEN_DGTZ_SetChannelSelfTrigger(handle,CAEN_DGTZ_TRGMODE_DISABLED, (1 << ch));			
			if (ret)
				printf("Warning: error disabling ch %d self trigger\n", ch);


			cal_ok[ch] = Calibration_is_possible(handle, ch, WDcfg, BoardInfo);
			if (cal_ok[ch])
			{
				for (p = 0; p < NPOINTS; p++)
				{
					ret = CAEN_DGTZ_SetChannelDCOffset(handle, (uint32_t)ch, (uint32_t)((float)(abs(dc[p] - 100))*(655.35)));
					if (ret)
						printf("Warning: error setting ch %d test offset\n", ch);
#ifdef _WIN32
					Sleep(200);
#else
					usleep(200000);
#endif

					int value[NACQS] = { 0 };
					for (acq = 0; acq < NACQS; acq++)
					{
						CAEN_DGTZ_SendSWtrigger(handle);

						ret = CAEN_DGTZ_ReadData(handle, CAEN_DGTZ_SLAVE_TERMINATED_READOUT_MBLT, buffer, &BufferSize);
						if (ret) {
							ErrCode = ERR_READOUT;
							goto QuitProgram;
						}

						ret = CAEN_DGTZ_GetEventInfo(handle, buffer, BufferSize, 0, &EventInfo, &EventPtr);
						if (ret) {
							ErrCode = ERR_EVENT_BUILD;
							goto QuitProgram;
						}
						// decode the event //
						if (WDcfg.Nbit == 8)
							ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event8);
						else
							ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event16);

						if (ret) {
							ErrCode = ERR_EVENT_BUILD;
							goto QuitProgram;
						}


						for (i = 1; i < 7; i++) //mean over 6 samples
						{
							if (WDcfg.Nbit == 8)
								value[acq] += (int)(Event8->DataChannel[ch][i]);
							else
								value[acq] += (int)(Event16->DataChannel[ch][i]);
						}
						value[acq] = (value[acq] / 6);

					}//for acq

				 ///check for clean baselines
					int max = 0;
					int mpp = 0;
					int size = (int)pow(2, (double)BoardInfo.ADC_NBits);
					int *freq = calloc(size, sizeof(int));

					for (k = 0; k < NACQS; k++)
					{
						if (value[k] > 0 && value[k] < size)
						{
							freq[value[k]]++;
							if (freq[value[k]] > max) { max = freq[value[k]]; mpp = value[k]; }
						}
					}

					free(freq);
					int ok = 0;
					for (k = 0; k < NACQS; k++)
					{
						if (value[k] == mpp || value[k] == (mpp + 1) || value[k] == (mpp - 1))
						{
							avg_value[p] = avg_value[p] + (float)value[k]; ok++;
						}
					}
					avg_value[p] = (avg_value[p] / (float)ok)*100. / (float)size;

				}//close for p
				cal = ((float)(avg_value[1] - avg_value[0]) / (float)(dc[1] - dc[0]));
				offset = (float)(dc[1] * avg_value[0] - dc[0] * avg_value[1]) / (float)(dc[1] - dc[0]);
				//printf("Cal %f   offset %f\n", cal, offset);
			  }///close if calibration is possible
			

				if (WDcfg.PulsePolarity[ch] == CAEN_DGTZ_PulsePolarityPositive)
				{
					WDcfg.DCoffset[ch] = (uint32_t)((float)(fabs(( ((float)dc_file[ch] - offset )/ cal ) - 100.))*(655.35));
					if (WDcfg.DCoffset[ch] > 65535) WDcfg.DCoffset[ch] = 65535;
					if (WDcfg.DCoffset[ch] < 0) WDcfg.DCoffset[ch] = 0;
				}
				else
					if (WDcfg.PulsePolarity[ch] == CAEN_DGTZ_PulsePolarityNegative)
					{
						WDcfg.DCoffset[ch] = (uint32_t)((float)(fabs(( (fabs(dc_file[ch] - 100.) - offset) / cal ) - 100.))*(655.35));
						if (WDcfg.DCoffset[ch] < 0) WDcfg.DCoffset[ch] = 0;
						if (WDcfg.DCoffset[ch] > 65535) WDcfg.DCoffset[ch] = 65535;

					}

				ret = CAEN_DGTZ_SetChannelDCOffset(handle, (uint32_t)ch, WDcfg.DCoffset[ch]);
				if (ret)
					printf("Warning: error setting ch %d offset\n", ch);
#ifdef _WIN32
				Sleep(200);
#else
				usleep(200000);
#endif
		}//if ch enabled

	}//loop ch

	//printf("DAC Calibration ready\n");

	CAEN_DGTZ_SWStopAcquisition(handle);  

	///free events e buffer
	CAEN_DGTZ_FreeReadoutBuffer(&buffer);
	if (WDcfg.Nbit == 8)
		CAEN_DGTZ_FreeEvent(handle, (void**)&Event8);
	else
		CAEN_DGTZ_FreeEvent(handle, (void**)&Event16);

	Set_correct_Threshold(handle, WDcfg, BoardInfo);

	ret |= CAEN_DGTZ_SetPostTriggerSize(handle, WDcfg.PostTrigger);
	ret |= CAEN_DGTZ_SetAcquisitionMode(handle, mem_mode);
	ret |= CAEN_DGTZ_SetExtTriggerInputMode(handle, WDcfg.ExtTriggerMode);
	if (ret)
		printf("Warning: error setting recorded parameters\n");


QuitProgram:
	if (ErrCode) {
		printf("\a%s\n", ErrMsg[ErrCode]);
#ifdef WIN32
		printf("Press a key to quit\n");
		getch();
#endif
	}
	
}


/*! \fn      void Set_correct_Threshold(int handle, WaveDumpConfig_t WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo)
*   \brief   sets the trigger threshold relative to the baseline (only if BASELINE_SHIFT is in use)
*
*   \param   handle   Digitizer handle
*   \param   WDcfg:   Pointer to the WaveDumpConfig_t data structure
*   \param   BoardInfo: structure with the board info
*/
void Set_correct_Threshold(int handle, WaveDumpConfig_t WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo)
{
	int i = 0,ch=0;
	CAEN_DGTZ_ErrorCode ret;
	uint32_t  AllocatedSize;

	ERROR_CODES ErrCode = ERR_NONE;
	uint32_t BufferSize;
	CAEN_DGTZ_EventInfo_t       EventInfo;
	char *buffer = NULL;
	char *EventPtr = NULL;
	CAEN_DGTZ_UINT16_EVENT_t    *Event16 = NULL;
	CAEN_DGTZ_UINT8_EVENT_t     *Event8 = NULL;

	///malloc
	ret = CAEN_DGTZ_MallocReadoutBuffer(handle, &buffer, &AllocatedSize);
	if (ret) {
		ErrCode = ERR_MALLOC;
		goto QuitProgram;
	}

	if (WDcfg.Nbit == 8)
		ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event8);
	else {
			ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event16);	
	}
	if (ret != CAEN_DGTZ_Success) {
		ErrCode = ERR_MALLOC;
		goto QuitProgram;
	}

	uint32_t mask;
	CAEN_DGTZ_GetChannelEnableMask(handle, &mask);

	CAEN_DGTZ_SWStartAcquisition(handle);
	for (ch = 0; ch < (int32_t)BoardInfo.Channels; ch++)
	{

		if (WDcfg.EnableMask & (1 << ch) && WDcfg.Version_used[ch] == 1)
		{
			if (cal_ok[ch])
			{
				int baseline = 0;
				CAEN_DGTZ_SendSWtrigger(handle);

				ret = CAEN_DGTZ_ReadData(handle, CAEN_DGTZ_SLAVE_TERMINATED_READOUT_MBLT, buffer, &BufferSize);
				if (ret) {
					ErrCode = ERR_READOUT;
					goto QuitProgram;
				}

				ret = CAEN_DGTZ_GetEventInfo(handle, buffer, BufferSize, 0, &EventInfo, &EventPtr);
				if (ret) {
					ErrCode = ERR_EVENT_BUILD;
					goto QuitProgram;
				}
				// decode the event //
				if (WDcfg.Nbit == 8)
					ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event8);
				else
					ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event16);

				if (ret) {
					ErrCode = ERR_EVENT_BUILD;
					goto QuitProgram;
				}


				for (i = 1; i < 11; i++) //mean over 10 samples
				{
					if (WDcfg.Nbit == 8)
						baseline += (int)(Event8->DataChannel[ch][i]);
					else
						baseline += (int)(Event16->DataChannel[ch][i]);

				}
				baseline = (baseline / 10);

				if (WDcfg.PulsePolarity[ch] == CAEN_DGTZ_PulsePolarityPositive)
					WDcfg.Threshold[ch] = (uint32_t)baseline + thr_file[ch];
				else 	if (WDcfg.PulsePolarity[ch] == CAEN_DGTZ_PulsePolarityNegative)
					WDcfg.Threshold[ch] = (uint32_t)baseline - thr_file[ch];

				if (WDcfg.Threshold[ch] < 0) WDcfg.Threshold[ch] = 0;
				int size = (int)pow(2, (double)BoardInfo.ADC_NBits);
				if (WDcfg.Threshold[ch] > (uint32_t)size) WDcfg.Threshold[ch] = size;
			}//if cal ok ch
			else
				WDcfg.Threshold[ch] = thr_file[ch];

				ret = CAEN_DGTZ_SetChannelTriggerThreshold(handle, ch, WDcfg.Threshold[ch]);
				if (ret)
					printf("Warning: error setting ch %d corrected threshold\n", ch);

				ret |= CAEN_DGTZ_SetChannelSelfTrigger(handle, WDcfg.ChannelTriggerMode[ch], (1 << ch));

		}
	}
	CAEN_DGTZ_SWStopAcquisition(handle);

	CAEN_DGTZ_FreeReadoutBuffer(&buffer);
	if (WDcfg.Nbit == 8)
		CAEN_DGTZ_FreeEvent(handle, (void**)&Event8);
	else
		CAEN_DGTZ_FreeEvent(handle, (void**)&Event16);


QuitProgram:
	if (ErrCode) {
		printf("\a%s\n", ErrMsg[ErrCode]);
#ifdef WIN32
		printf("Press a key to quit\n");
		getch();
#endif
	}
}

/*! \fn      void CheckKeyboardCommands(WaveDumpRun_t *WDrun)
*   \brief   check if there is a key pressed and execute the relevant command
*
*   \param   WDrun:   Pointer to the WaveDumpRun_t data structure
*   \param   WDcfg:   Pointer to the WaveDumpConfig_t data structure
*   \param   BoardInfo: structure with the board info
*/
void CheckKeyboardCommands(int handle, WaveDumpRun_t *WDrun, WaveDumpConfig_t *WDcfg, CAEN_DGTZ_BoardInfo_t BoardInfo)
{
    int c = 0;

    if(!kbhit())
        return;

    c = getch();
    if ((c < '9') && (c >= '0')) {
        int ch = c-'0';
        if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE) || (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE)){
            if ( (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) && (WDcfg->FastTriggerEnabled == 0) && (ch == 8)) WDrun->ChannelPlotMask = WDrun->ChannelPlotMask ;
			else WDrun->ChannelPlotMask ^= (1 << ch);
            
			if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE) && (ch == 8)) printf("Channel %d belongs to a different group\n", ch + WDrun->GroupPlotIndex * 8);
			else
			if (WDrun->ChannelPlotMask & (1 << ch))
                printf("Channel %d enabled for plotting\n", ch + WDrun->GroupPlotIndex*8);
            else
                printf("Channel %d disabled for plotting\n", ch + WDrun->GroupPlotIndex*8);
        } 
		else if((BoardInfo.FamilyCode == CAEN_DGTZ_XX730_FAMILY_CODE) || (BoardInfo.FamilyCode == CAEN_DGTZ_XX725_FAMILY_CODE) && (WDcfg->Nch>8)) {
		ch = ch + 8 * WDrun->GroupPlotSwitch;
		if(ch!= 8 && WDcfg->EnableMask & (1 << ch)){		
		WDrun->ChannelPlotMask ^= (1 << ch);
		if (WDrun->ChannelPlotMask & (1 << ch))
		printf("Channel %d enabled for plotting\n", ch);
		else
		printf("Channel %d disabled for plotting\n", ch);
		}
		else printf("Channel %d not enabled for acquisition\n",ch);
		}			
		else {
            WDrun->ChannelPlotMask ^= (1 << ch);
            if (WDrun->ChannelPlotMask & (1 << ch))
                printf("Channel %d enabled for plotting\n", ch);
            else
                printf("Channel %d disabled for plotting\n", ch);
        }
    } else {
        switch(c) {
        case 'g' :
			//for boards with >8 channels
			if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX730_FAMILY_CODE) || (BoardInfo.FamilyCode == CAEN_DGTZ_XX725_FAMILY_CODE) && (WDcfg->Nch > 8))
			{
				if (WDrun->GroupPlotSwitch == 0) {
					WDrun->GroupPlotSwitch = 1;
					printf("Channel group set to %d: use numbers 0-7 for channels 8-15\n", WDrun->GroupPlotSwitch);
				}
				else if(WDrun->GroupPlotSwitch == 1)	{
					WDrun->GroupPlotSwitch = 0;
					printf("Channel group set to %d: use numbers 0-7 for channels 0-7\n", WDrun->GroupPlotSwitch);
				}
			}
			else
            // Update the group plot index
            if ((WDcfg->EnableMask) && (WDcfg->Nch>8))
                GoToNextEnabledGroup(WDrun, WDcfg);
            break;
        case 'q' :
            WDrun->Quit = 1;
            break;
        case 'R' :
            WDrun->Restart = 1;
            break;
        case 't' :
            if (!WDrun->ContinuousTrigger) {
                CAEN_DGTZ_SendSWtrigger(handle);
                printf("Single Software Trigger issued\n");
            }
            break;
        case 'T' :
            WDrun->ContinuousTrigger ^= 1;
            if (WDrun->ContinuousTrigger)
                printf("Continuous trigger is enabled\n");
            else
                printf("Continuous trigger is disabled\n");
            break;
        case 'P' :
            if (WDrun->ChannelPlotMask == 0)
                printf("No channel enabled for plotting\n");
            else
                WDrun->ContinuousPlot ^= 1;
            break;
        case 'p' :
            if (WDrun->ChannelPlotMask == 0)
                printf("No channel enabled for plotting\n");
            else
                WDrun->SinglePlot = 1;
            break;
        case 'f' :
            WDrun->PlotType = (WDrun->PlotType == PLOT_FFT) ? PLOT_WAVEFORMS : PLOT_FFT;
            WDrun->SetPlotOptions = 1;
            break;
        case 'h' :
            WDrun->PlotType = (WDrun->PlotType == PLOT_HISTOGRAM) ? PLOT_WAVEFORMS : PLOT_HISTOGRAM;
            WDrun->RunHisto = (WDrun->PlotType == PLOT_HISTOGRAM);
            WDrun->SetPlotOptions = 1;
            break;
        case 'w' :
            if (!WDrun->ContinuousWrite)
                WDrun->SingleWrite = 1;
            break;
        case 'W' :
            WDrun->ContinuousWrite ^= 1;
            if (WDrun->ContinuousWrite)
                printf("Continuous writing is enabled\n");
            else
                printf("Continuous writing is disabled\n");
            break;
        case 's' :
            if (WDrun->AcqRun == 0) {
                // Avoid calibration for X731 (it is done automatically when
                // switching DES mode enablement.
				if (BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE)//XX740 specific
				Calibrate_XX740_DC_Offset(handle, *WDcfg, BoardInfo);
				else if (BoardInfo.FamilyCode != CAEN_DGTZ_XX742_FAMILY_CODE)//XX742 not considered
				Calibrate_DC_Offset(handle, *WDcfg, BoardInfo);

				if (BoardInfo.FamilyCode == CAEN_DGTZ_XX730_FAMILY_CODE || BoardInfo.FamilyCode == CAEN_DGTZ_XX725_FAMILY_CODE)
					WDrun->GroupPlotSwitch = 0;
				
                printf("Acquisition started\n");

                CAEN_DGTZ_SWStartAcquisition(handle);

                WDrun->AcqRun = 1;

            } else {
                printf("Acquisition stopped\n");
                CAEN_DGTZ_SWStopAcquisition(handle);
                WDrun->AcqRun = 0;
				//WDrun->Restart = 1;
            }
            break;
        case 'm' :
            if (BoardSupportsTemperatureRead(BoardInfo)) {
                if (WDrun->AcqRun == 0) {
                    int32_t ch;
                    for (ch = 0; ch < (int32_t)BoardInfo.Channels; ch++) {
                        uint32_t temp;
                        int32_t ret = CAEN_DGTZ_ReadTemperature(handle, ch, &temp);
                        printf("CH%02d: ", ch);
                        if (ret == CAEN_DGTZ_Success)
                            printf("%u C\n", temp);
                        else
                            printf("CAENDigitizer ERR %d\n", ret);
                    }
                    printf("\n");
                }
                else {
                    printf("Can't run temperature monitor while acquisition is running.\n");
                }
            }
            else {
                printf("Board Family doesn't support ADC Temperature Monitor.\n");
            }
            break;
        case 'c' :
            calibrate(handle, WDrun, BoardInfo);
            break;
        case ' ' :
            printf("\n                            Bindkey help                                \n");
            printf("--------------------------------------------------------------------------\n");;
            printf("  [q]   Quit\n");
            printf("  [R]   Reload configuration file and restart\n");
            printf("  [s]   Start/Stop acquisition\n");
            printf("  [t]   Send a software trigger (single shot)\n");
            printf("  [T]   Enable/Disable continuous software trigger\n");
            printf("  [w]   Write one event to output file\n");
            printf("  [W]   Enable/Disable continuous writing to output file\n");
            printf("  [p]   Plot one event\n");
            printf("  [P]   Enable/Disable continuous plot\n");
            printf("  [f]   Toggle between FFT and Waveform plot\n");
            printf("  [h]   Toggle between Histogram and Waveform plot\n");
            printf("  [g]   Change the index of the group to plot (XX740 family)\n");
            printf("  [m]   Single ADC temperature monitor (XX751/30/25 only)\n");
            printf("  [c]   ADC Calibration (XX751/30/25 only)\n");
            printf(" [0-7]  Enable/Disable one channel on the plot\n");
            printf("        For x740 family this is the plotted group's relative channel index\n");
            printf("[SPACE] This help\n");
            printf("--------------------------------------------------------------------------\n");
            printf("Press a key to continue\n");
            getch();
            break;
        default :   break;
        }
    }
}

/*! \brief   Write the event data into the output files
*
*   \param   WDrun Pointer to the WaveDumpRun data structure
*   \param   WDcfg Pointer to the WaveDumpConfig data structure
*   \param   EventInfo Pointer to the EventInfo data structure
*   \param   Event Pointer to the Event to write
*/
int WriteOutputFiles(WaveDumpConfig_t *WDcfg, WaveDumpRun_t *WDrun, CAEN_DGTZ_EventInfo_t *EventInfo, void *Event)
{
    int ch, j, ns;
    CAEN_DGTZ_UINT16_EVENT_t  *Event16 = NULL;
    CAEN_DGTZ_UINT8_EVENT_t   *Event8 = NULL;

    if (WDcfg->Nbit == 8)
        Event8 = (CAEN_DGTZ_UINT8_EVENT_t *)Event;
    else
        Event16 = (CAEN_DGTZ_UINT16_EVENT_t *)Event;

    for (ch = 0; ch < WDcfg->Nch; ch++) {
        int Size = (WDcfg->Nbit == 8) ? Event8->ChSize[ch] : Event16->ChSize[ch];
        if (Size <= 0) {
            continue;
        }

        // Check the file format type
        if( WDcfg->OutFileFlags& OFF_BINARY) {
            // Binary file format
            uint32_t BinHeader[6];
            BinHeader[0] = (WDcfg->Nbit == 8) ? Size + 6*sizeof(*BinHeader) : Size*2 + 6*sizeof(*BinHeader);
            BinHeader[1] = EventInfo->BoardId;
            BinHeader[2] = EventInfo->Pattern;
            BinHeader[3] = ch;
            BinHeader[4] = EventInfo->EventCounter;
            BinHeader[5] = EventInfo->TriggerTimeTag;
            if (!WDrun->fout[ch]) {
                char fname[100];
                sprintf(fname, "wave%d.dat", ch);
                if ((WDrun->fout[ch] = fopen(fname, "wb")) == NULL)
                    return -1;
            }
            if( WDcfg->OutFileFlags & OFF_HEADER) {
                // Write the Channel Header
                if(fwrite(BinHeader, sizeof(*BinHeader), 6, WDrun->fout[ch]) != 6) {
                    // error writing to file
                    fclose(WDrun->fout[ch]);
                    WDrun->fout[ch]= NULL;
                    return -1;
                }
            }
            if (WDcfg->Nbit == 8)
                ns = (int)fwrite(Event8->DataChannel[ch], 1, Size, WDrun->fout[ch]);
            else
                ns = (int)fwrite(Event16->DataChannel[ch] , 1 , Size*2, WDrun->fout[ch]) / 2;
            if (ns != Size) {
                // error writing to file
                fclose(WDrun->fout[ch]);
                WDrun->fout[ch]= NULL;
                return -1;
            }
        } else {
            // Ascii file format
            if (!WDrun->fout[ch]) {
                char fname[100];
                sprintf(fname, "wave%d.txt", ch);
                if ((WDrun->fout[ch] = fopen(fname, "w")) == NULL)
                    return -1;
            }
            if( WDcfg->OutFileFlags & OFF_HEADER) {
                // Write the Channel Header
                fprintf(WDrun->fout[ch], "Record Length: %d\n", Size);
                fprintf(WDrun->fout[ch], "BoardID: %2d\n", EventInfo->BoardId);
                fprintf(WDrun->fout[ch], "Channel: %d\n", ch);
                fprintf(WDrun->fout[ch], "Event Number: %d\n", EventInfo->EventCounter);
                fprintf(WDrun->fout[ch], "Pattern: 0x%04X\n", EventInfo->Pattern & 0xFFFF);
                fprintf(WDrun->fout[ch], "Trigger Time Stamp: %u\n", EventInfo->TriggerTimeTag);
                fprintf(WDrun->fout[ch], "DC offset (DAC): 0x%04X\n", WDcfg->DCoffset[ch] & 0xFFFF);
            }
            for(j=0; j<Size; j++) {
                if (WDcfg->Nbit == 8)
                    fprintf(WDrun->fout[ch], "%d\n", Event8->DataChannel[ch][j]);
                else
                    fprintf(WDrun->fout[ch], "%d\n", Event16->DataChannel[ch][j]);
            }
        }
        if (WDrun->SingleWrite) {
            fclose(WDrun->fout[ch]);
            WDrun->fout[ch]= NULL;
        }
    }
    return 0;

}

/*! \brief   Write the event data on x742 boards into the output files
*
*   \param   WDrun Pointer to the WaveDumpRun data structure
*   \param   WDcfg Pointer to the WaveDumpConfig data structure
*   \param   EventInfo Pointer to the EventInfo data structure
*   \param   Event Pointer to the Event to write
*/
int WriteOutputFilesx742(WaveDumpConfig_t *WDcfg, WaveDumpRun_t *WDrun, CAEN_DGTZ_EventInfo_t *EventInfo, CAEN_DGTZ_X742_EVENT_t *Event, char *outdir)
{
    int gr,ch, j, ns;
    char trname[10], flag = 0;
	

	// trigger counts and logic: channel 0, group 0, around 750 ns
	if(Event->DataGroup[0].DataChannel[0][750] < 1000) {
		if(totCounter_muon > maxtrig_muon) return 0;
		totCounter_muon += 1;
	}
	else {
		if(totCounter_rdm > maxtrig_rdm) return 0;
		totCounter_rdm += 1;
	}
	
	
    for (gr=0;gr<(WDcfg->Nch/8);gr++) {
        if (Event->GrPresent[gr]) {
            for(ch=0; ch<9; ch++) {
                int Size = Event->DataGroup[gr].ChSize[ch];
                if (Size <= 0) {
                    continue;
                }

                // Check the file format type
                if( WDcfg->OutFileFlags& OFF_BINARY) {
                    // Binary file format
                    uint32_t BinHeader[6];
                    BinHeader[0] = (WDcfg->Nbit == 8) ? Size + 6*sizeof(*BinHeader) : Size*4 + 6*sizeof(*BinHeader);
                    BinHeader[1] = EventInfo->BoardId;
                    BinHeader[2] = EventInfo->Pattern;
                    BinHeader[3] = ch;
                    BinHeader[4] = EventInfo->EventCounter;
                    BinHeader[5] = EventInfo->TriggerTimeTag;
                    if (!WDrun->fout[(gr*9+ch)]) {
                        char fname[100];
                        if ((gr*9+ch) == 8) {
                            sprintf(fname, "TR_%d_0.dat", gr);
                            sprintf(trname,"TR_%d_0",gr);
                            flag = 1;
                        }
                        else if ((gr*9+ch) == 17) {
                            sprintf(fname, "TR_0_%d.dat", gr);
                            sprintf(trname,"TR_0_%d",gr);
                            flag = 1;
                        }
                        else if ((gr*9+ch) == 26) {
                            sprintf(fname, "TR_0_%d.dat", gr);
                            sprintf(trname,"TR_0_%d",gr);
                            flag = 1;
                        }
                        else if ((gr*9+ch) == 35) {
                            sprintf(fname, "TR_1_%d.dat", gr);
                            sprintf(trname,"TR_1_%d",gr);
                            flag = 1;
                        }
                        else 	{
                            sprintf(fname, "%s/wave_%d.dat", outdir, (gr*8)+ch);
                            flag = 0;
                        }
                        if ((WDrun->fout[(gr*9+ch)] = fopen(fname, "wb")) == NULL)
                            return -1;
                    }
                    if( WDcfg->OutFileFlags & OFF_HEADER) {
                        // Write the Channel Header
                        if(fwrite(BinHeader, sizeof(*BinHeader), 6, WDrun->fout[(gr*9+ch)]) != 6) {
                            // error writing to file
                            fclose(WDrun->fout[(gr*9+ch)]);
                            WDrun->fout[(gr*9+ch)]= NULL;
                            return -1;
                        }
                    }
                    ns = (int)fwrite( Event->DataGroup[gr].DataChannel[ch] , 1 , Size*4, WDrun->fout[(gr*9+ch)]) / 4;
                    if (ns != Size) {
                        // error writing to file
                        fclose(WDrun->fout[(gr*9+ch)]);
                        WDrun->fout[(gr*9+ch)]= NULL;
                        return -1;
                    }
                } else {
                    // Ascii file format
                    if (!WDrun->fout[(gr*9+ch)]) {
                        char fname[100];
                        if ((gr*9+ch) == 8) {
                            //sprintf(fname, "TR_%d_0.txt", gr);
							sprintf(fname, "%s/TR_%d_0.txt", outdir, gr);
                            sprintf(trname,"TR_%d_0",gr);
                            flag = 1;
                        }
                        else if ((gr*9+ch) == 17) {
                            //sprintf(fname, "TR_0_%d.txt", gr);
							sprintf(fname, "%s/TR_0_%d.txt", outdir, gr);
                            sprintf(trname,"TR_0_%d",gr);
                            flag = 1;
                        }
                        else if ((gr*9+ch) == 26) {
                            //sprintf(fname, "TR_0_%d.txt", gr);
							sprintf(fname, "%s/TR_0_%d.txt", outdir, gr);
                            sprintf(trname,"TR_0_%d",gr);
                            flag = 1;
                        }
                        else if ((gr*9+ch) == 35) {
                            //sprintf(fname, "TR_1_%d.txt", gr);
							sprintf(fname, "%s/TR_1_%d.txt", outdir, gr);
                            sprintf(trname,"TR_1_%d",gr);
                            flag = 1;
                        }
                        else 	{
                            sprintf(fname, "%s/wave_%d.txt", outdir, (gr*8)+ch);
                            flag = 0;
                        }
                        if ((WDrun->fout[(gr*9+ch)] = fopen(fname, "w")) == NULL)
                            return -1;
                    }
					

                    if( WDcfg->OutFileFlags & OFF_HEADER) {
                        // Write the Channel Header
                        fprintf(WDrun->fout[(gr*9+ch)], "Record Length: %d\n", Size);
                        fprintf(WDrun->fout[(gr*9+ch)], "BoardID: %2d\n", EventInfo->BoardId);
                        if (flag)
                            fprintf(WDrun->fout[(gr*9+ch)], "Channel: %s\n",  trname);
                        else
                            fprintf(WDrun->fout[(gr*9+ch)], "Channel: %d\n",  (gr*8)+ ch);
                        fprintf(WDrun->fout[(gr*9+ch)], "Event Number: %d\n", EventInfo->EventCounter);
                        fprintf(WDrun->fout[(gr*9+ch)], "Pattern: 0x%04X\n", EventInfo->Pattern & 0xFFFF);
                        fprintf(WDrun->fout[(gr*9+ch)], "Trigger Time Stamp: %u\n", Event->DataGroup[gr].TriggerTimeTag);
                        fprintf(WDrun->fout[(gr*9+ch)], "DC offset (DAC): 0x%04X\n", WDcfg->DCoffset[ch] & 0xFFFF);
                        fprintf(WDrun->fout[(gr*9+ch)], "Start Index Cell: %d\n", Event->DataGroup[gr].StartIndexCell);
                        flag = 0;
                    }
                    for(j=0; j<Size; j++) {
                        fprintf(WDrun->fout[(gr*9+ch)], "%f\n", Event->DataGroup[gr].DataChannel[ch][j]);
                    }
					
					//printf("%d %f %f\n", j, Event->DataGroup[0].DataChannel[0][100], );
					//printf("******************************************************************\n");
                }
                if (WDrun->SingleWrite) {
                    fclose(WDrun->fout[(gr*9+ch)]);
                    WDrun->fout[(gr*9+ch)]= NULL;
                }
            }
        }
    }
    return 0;

}

/* ########################################################################### */
/* MAIN                                                                        */
/* ########################################################################### */
int main(int argc, char *argv[])
{
      
    WaveDumpConfig_t   WDcfg;
    WaveDumpRun_t      WDrun;
    CAEN_DGTZ_ErrorCode ret = CAEN_DGTZ_Success;
    int  handle = -1;
    ERROR_CODES ErrCode= ERR_NONE;
    int i, ch, Nb=0, Ne=0;
    uint32_t AllocatedSize, BufferSize, NumEvents;
    char *buffer = NULL;
    char *EventPtr = NULL;
    char ConfigFileName[100];
    int isVMEDevice= 0, MajorNumber;
    uint64_t CurrentTime, PrevRateTime, ElapsedTime;
    int nCycles= 0;
    CAEN_DGTZ_BoardInfo_t       BoardInfo;
    CAEN_DGTZ_EventInfo_t       EventInfo;

    CAEN_DGTZ_UINT16_EVENT_t    *Event16=NULL; /* generic event struct with 16 bit data (10, 12, 14 and 16 bit digitizers */

    CAEN_DGTZ_UINT8_EVENT_t     *Event8=NULL; /* generic event struct with 8 bit data (only for 8 bit digitizers) */ 
    CAEN_DGTZ_X742_EVENT_t       *Event742=NULL;  /* custom event struct with 8 bit data (only for 8 bit digitizers) */
    WDPlot_t                    *PlotVar=NULL;
    FILE *f_ini;
    CAEN_DGTZ_DRS4Correction_t X742Tables[MAX_X742_GROUP_SIZE];

    int ReloadCfgStatus = 0x7FFFFFFF; // Init to the bigger positive number
    
    // Get max triggers and run ID
    int runid, hvpoint;
    if (argc == 5) {
        
        maxtrig_rdm = atoi(argv[1]);
		maxtrig_muon = atoi(argv[2]);
        runid = atoi(argv[3]);
        hvpoint = atoi(argv[4]);
    }
	else {
		exit(0);
	}
    
    
    
    char log[1000], msg[1000], outdir[1000], setrun[1000], runfile[1000];
    sprintf(log, "/var/webdcs/HVSCAN/%06d/log.txt", runid); // remote log file
    sprintf(outdir, "/var/webdcs/HVSCAN/%06d/HV%d_DIGITIZER/", runid, hvpoint); // destination dir

    
    sprintf(setrun, "INIT");
    setRunFile(setrun);

    /* *************************************************************************************** */
    /* Open and parse configuration file                                                       */
    /* *************************************************************************************** */
    memset(&WDrun, 0, sizeof(WDrun));
    memset(&WDcfg, 0, sizeof(WDcfg));
    
   
    
    sprintf(msg, "Start CAEN DIGITIZER DT5742 DAQ");
    logEntry(msg, log);
    sprintf(msg, "Reading configuration file");
    logEntry(msg, log);
    
    f_ini = fopen("/var/webdcs/RUN/cfg_digitizer_daq.ini", "r");
    if (f_ini == NULL ) {
        ErrCode = ERR_CONF_FILE_NOT_FOUND;
        goto QuitProgram;
    } 
    ParseConfigFile(f_ini, &WDcfg);
    fclose(f_ini);
    


    /* *************************************************************************************** */
    /* Open the digitizer and read the board information                                       */
    /* *************************************************************************************** */
    isVMEDevice = WDcfg.BaseAddress ? 1 : 0;

    ret = CAEN_DGTZ_OpenDigitizer(WDcfg.LinkType, WDcfg.LinkNum, WDcfg.ConetNode, WDcfg.BaseAddress, &handle);
    if (ret) {
        ErrCode = ERR_DGZ_OPEN;
        
        goto QuitProgram;
    }

    ret = CAEN_DGTZ_GetInfo(handle, &BoardInfo);
    if (ret) {
        ErrCode = ERR_BOARD_INFO_READ;
        goto QuitProgram;
    }
    
    
    
    
    
    sprintf(msg, "Connected to CAEN Digitizer Model %s", BoardInfo.ModelName);
    logEntry(msg, log);
    sprintf(msg, "ROC FPGA Release is %s", BoardInfo.ROC_FirmwareRel);
    logEntry(msg, log);
    sprintf(msg, "AMC FPGA Release is %s", BoardInfo.AMC_FirmwareRel);
    logEntry(msg, log);

    // Check firmware rivision (DPP firmwares cannot be used with WaveDump */
    sscanf(BoardInfo.AMC_FirmwareRel, "%d", &MajorNumber);
    if (MajorNumber >= 128) {
        sprintf(msg, "This digitizer has a DPP firmware");
        logEntry(msg, log);
        ErrCode = ERR_INVALID_BOARD_TYPE;
        goto QuitProgram;
    }
    

    
	//Check if model x742 is in use
	/*
	if (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) {

		printf("\nWARNING: using configuration file /etc/wavedump/WaveDumpConfig_X742.txt specific for Board model X742.\nEdit this file if you want to modify the default settings.\n ");
 #ifdef LINUX 
	     strcpy(ConfigFileName, "/etc/wavedump/WaveDumpConfig_X742.txt");
 #else 
	     strcpy(ConfigFileName, "WaveDumpConfig_X742.txt");
 #endif
		f_ini = fopen(ConfigFileName, "r");
		if (f_ini == NULL) {
			ErrCode = ERR_CONF_FILE_NOT_FOUND;
			goto QuitProgram;
		}
		ParseConfigFile(f_ini, &WDcfg);
		fclose(f_ini);
	}
	*/

    // Get Number of Channels, Number of bits, Number of Groups of the board */
    ret = GetMoreBoardInfo(handle, BoardInfo, &WDcfg);
    if (ret) {
        ErrCode = ERR_INVALID_BOARD_TYPE;
        goto QuitProgram;
    }

    // Perform calibration (if needed).
    if (WDcfg.StartupCalibration)
        calibrate(handle, &WDrun, BoardInfo);


    sprintf(setrun, "DAQ_RDY");
    setRunFile(setrun);
    
    while(1) { // wait for START command from webdcs
        
        if(strcmp(runfile, "START") == 0) break;
        fflush(stdout);
        sleep(1);
        readRunFile(runfile);
        
        printf("WAIT...\n");
        fflush(stdout);
    }

    

    sprintf(setrun, "RUNNING");
    setRunFile(setrun);
    

Restart:
    // mask the channels not available for this model
    if ((BoardInfo.FamilyCode != CAEN_DGTZ_XX740_FAMILY_CODE) && (BoardInfo.FamilyCode != CAEN_DGTZ_XX742_FAMILY_CODE)){
        WDcfg.EnableMask &= (1<<WDcfg.Nch)-1;
    } else {
        WDcfg.EnableMask &= (1<<(WDcfg.Nch/8))-1;
    }
    if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX751_FAMILY_CODE) && WDcfg.DesMode) {
        WDcfg.EnableMask &= 0xAA;
    }
    if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX731_FAMILY_CODE) && WDcfg.DesMode) {
        WDcfg.EnableMask &= 0x55;
    }
    // Set plot mask
    if ((BoardInfo.FamilyCode != CAEN_DGTZ_XX740_FAMILY_CODE) && (BoardInfo.FamilyCode != CAEN_DGTZ_XX742_FAMILY_CODE)){
        WDrun.ChannelPlotMask = WDcfg.EnableMask;
    } else {
        WDrun.ChannelPlotMask = (WDcfg.FastTriggerEnabled == 0) ? 0xFF: 0x1FF;
    }
	if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX730_FAMILY_CODE) || (BoardInfo.FamilyCode == CAEN_DGTZ_XX725_FAMILY_CODE)) {
		WDrun.GroupPlotSwitch = 0;
	}
    /* *************************************************************************************** */
    /* program the digitizer                                                                   */
    /* *************************************************************************************** */
    ret = ProgramDigitizer(handle, WDcfg, BoardInfo);
    if (ret) {
        ErrCode = ERR_DGZ_PROGRAM;
        goto QuitProgram;
    }

    // Select the next enabled group for plotting
    if ((WDcfg.EnableMask) && (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE))
        if( ((WDcfg.EnableMask>>WDrun.GroupPlotIndex)&0x1)==0 )
            GoToNextEnabledGroup(&WDrun, &WDcfg);

    // Read again the board infos, just in case some of them were changed by the programming
    // (like, for example, the TSample and the number of channels if DES mode is changed)
    if(ReloadCfgStatus > 0) {
        ret = CAEN_DGTZ_GetInfo(handle, &BoardInfo);
        if (ret) {
            ErrCode = ERR_BOARD_INFO_READ;
            goto QuitProgram;
        }
        ret = GetMoreBoardInfo(handle,BoardInfo, &WDcfg);
        if (ret) {
            ErrCode = ERR_INVALID_BOARD_TYPE;
            goto QuitProgram;
        }

        // Reload Correction Tables if changed
        if(BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE && (ReloadCfgStatus & (0x1 << CFGRELOAD_CORRTABLES_BIT)) ) {
            if(WDcfg.useCorrections != -1) { // Use Manual Corrections
                uint32_t GroupMask = 0;

                // Disable Automatic Corrections
                if ((ret = CAEN_DGTZ_DisableDRS4Correction(handle)) != CAEN_DGTZ_Success)
                    goto QuitProgram;

                // Load the Correction Tables from the Digitizer flash
                if ((ret = CAEN_DGTZ_GetCorrectionTables(handle, WDcfg.DRS4Frequency, (void*)X742Tables)) != CAEN_DGTZ_Success)
                    goto QuitProgram;

                if(WDcfg.UseManualTables != -1) { // The user wants to use some custom tables
                    uint32_t gr;
                    GroupMask = WDcfg.UseManualTables;

                    for(gr = 0; gr < WDcfg.MaxGroupNumber; gr++) {
                        if (((GroupMask>>gr)&0x1) == 0)
                            continue;
                        LoadCorrectionTable(WDcfg.TablesFilenames[gr], &(X742Tables[gr]));
                    }
                }
                // Save to file the Tables read from flash
                GroupMask = (~GroupMask) & ((0x1<<WDcfg.MaxGroupNumber)-1);
                SaveCorrectionTables("X742Table", GroupMask, X742Tables);
            }
            else { // Use Automatic Corrections
                if ((ret = CAEN_DGTZ_LoadDRS4CorrectionData(handle, WDcfg.DRS4Frequency)) != CAEN_DGTZ_Success)
                    goto QuitProgram;
                if ((ret = CAEN_DGTZ_EnableDRS4Correction(handle)) != CAEN_DGTZ_Success)
                    goto QuitProgram;
            }
        }
    }

    // Allocate memory for the event data and readout buffer
    if(WDcfg.Nbit == 8)
        ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event8);
    else {
        if (BoardInfo.FamilyCode != CAEN_DGTZ_XX742_FAMILY_CODE) {
            ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event16);
        }
        else {
            ret = CAEN_DGTZ_AllocateEvent(handle, (void**)&Event742);
        }
    }
    if (ret != CAEN_DGTZ_Success) {
        ErrCode = ERR_MALLOC;
        goto QuitProgram;
    }
    ret = CAEN_DGTZ_MallocReadoutBuffer(handle, &buffer,&AllocatedSize); /* WARNING: This malloc must be done after the digitizer programming */
    if (ret) {
        ErrCode = ERR_MALLOC;
        goto QuitProgram;
    }

    //if (WDcfg.TestPattern) CAEN_DGTZ_DisableDRS4Correction(handle);
    //else CAEN_DGTZ_EnableDRS4Correction(handle);

	if (WDrun.Restart && WDrun.AcqRun) 
	{
		if (BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE)//XX740 specific
			Calibrate_XX740_DC_Offset(handle, WDcfg, BoardInfo);
		else if (BoardInfo.FamilyCode != CAEN_DGTZ_XX742_FAMILY_CODE)//XX742 not considered
		    Calibrate_DC_Offset(handle, WDcfg, BoardInfo);

		CAEN_DGTZ_SWStartAcquisition(handle);
	}
    //else
    //    printf("[s] start/stop the acquisition, [q] quit, [SPACE] help\n");
    WDrun.Restart = 0;
    PrevRateTime = get_time();
    /* *************************************************************************************** */
    /* Readout Loop                                                                            */
    /* *************************************************************************************** */
    
    // Write in continuous mode
    WDrun.ContinuousWrite ^= 1;
    WDrun.AcqRun = 1;
    CAEN_DGTZ_SWStartAcquisition(handle);
    
	totCounter_rdm = 0;
    totCounter_muon = 0;
	int totCounter = 0;
	//printf("%d %d %d\n", totCounter, totCounter_rdm, totCounter_muon);
    while(!WDrun.Quit) {		
        // Check for keyboard commands (key pressed)
        //CheckKeyboardCommands(handle, &WDrun, &WDcfg, BoardInfo);
        if (WDrun.Restart) {
            CAEN_DGTZ_SWStopAcquisition(handle);
            CAEN_DGTZ_FreeReadoutBuffer(&buffer);
            ClosePlotter();
            PlotVar = NULL;
            if(WDcfg.Nbit == 8)
                CAEN_DGTZ_FreeEvent(handle, (void**)&Event8);
            else
                if (BoardInfo.FamilyCode != CAEN_DGTZ_XX742_FAMILY_CODE) {
                    CAEN_DGTZ_FreeEvent(handle, (void**)&Event16);
                }
                else {
                    CAEN_DGTZ_FreeEvent(handle, (void**)&Event742);
                }
                f_ini = fopen(ConfigFileName, "r");
                ReloadCfgStatus = ParseConfigFile(f_ini, &WDcfg);
                fclose(f_ini);
                goto Restart;
        }
        if (WDrun.AcqRun == 0)
            continue;

        /* Send a software trigger */
        if (WDrun.ContinuousTrigger) {
            CAEN_DGTZ_SendSWtrigger(handle);
        }

        /* Wait for interrupt (if enabled) */
        if (WDcfg.InterruptNumEvents > 0) {
            int32_t boardId;
            int VMEHandle = -1;
            int InterruptMask = (1 << VME_INTERRUPT_LEVEL);

            BufferSize = 0;
            NumEvents = 0;
            // Interrupt handling
            if (isVMEDevice) {
                ret = CAEN_DGTZ_VMEIRQWait ((CAEN_DGTZ_ConnectionType)WDcfg.LinkType, WDcfg.LinkNum, WDcfg.ConetNode, (uint8_t)InterruptMask, INTERRUPT_TIMEOUT, &VMEHandle);
            }
            else
                ret = CAEN_DGTZ_IRQWait(handle, INTERRUPT_TIMEOUT);
            if (ret == CAEN_DGTZ_Timeout)  // No active interrupt requests
                goto InterruptTimeout;
            if (ret != CAEN_DGTZ_Success)  {
                ErrCode = ERR_INTERRUPT;
                goto QuitProgram;
            }
            // Interrupt Ack
            if (isVMEDevice) {
                ret = CAEN_DGTZ_VMEIACKCycle(VMEHandle, VME_INTERRUPT_LEVEL, &boardId);
                if ((ret != CAEN_DGTZ_Success) || (boardId != VME_INTERRUPT_STATUS_ID)) {
                    goto InterruptTimeout;
                } else {
                    if (INTERRUPT_MODE == CAEN_DGTZ_IRQ_MODE_ROAK)
                        ret = CAEN_DGTZ_RearmInterrupt(handle);
                }
            }
        }

        /* Read data from the board */
        ret = CAEN_DGTZ_ReadData(handle, CAEN_DGTZ_SLAVE_TERMINATED_READOUT_MBLT, buffer, &BufferSize);
        if (ret) {

            ErrCode = ERR_READOUT;
            goto QuitProgram;
        }
        NumEvents = 0;
        if (BufferSize != 0) {
            ret = CAEN_DGTZ_GetNumEvents(handle, buffer, BufferSize, &NumEvents);
            if (ret) {
                ErrCode = ERR_READOUT;
                goto QuitProgram;
            }
        }
		else {
			uint32_t lstatus;
			ret = CAEN_DGTZ_ReadRegister(handle, CAEN_DGTZ_ACQ_STATUS_ADD, &lstatus);
			if (ret) {
				sprintf(msg, "Warning: Failure reading reg:%x (%d)\n", CAEN_DGTZ_ACQ_STATUS_ADD, ret);
                                logEntry(msg, log);
			}
			else {
				if (lstatus & (0x1 << 19)) {
					ErrCode = ERR_OVERTEMP;
					goto QuitProgram;
				}
			}
		}
InterruptTimeout:
        /* Calculate throughput and trigger rate (every second) */
        Nb += BufferSize;
        Ne += NumEvents;
        CurrentTime = get_time();
        ElapsedTime = CurrentTime - PrevRateTime;

        nCycles++;
        if (ElapsedTime > 1000) {
            if (Nb == 0)
                if (ret == CAEN_DGTZ_Timeout) printf ("Timeout...\n"); else printf("No data...\n");
            else {
                sprintf(msg, "Reading at %.2f MB/s (Trg Rate: %.2f Hz), random triggers = %d (%.0f%), muon triggers = %d (%.0f%)", (float)Nb/((float)ElapsedTime*1048.576f), (float)Ne*1000.0f/(float)ElapsedTime, totCounter_rdm, (float)100*totCounter_rdm/maxtrig_rdm, totCounter_muon, (float)100*totCounter_muon/maxtrig_muon);
                logEntry(msg, log);
				//printf("%d %d %d\n", totCounter, totCounter_rdm, totCounter_muon);
            }
            nCycles= 0;
            Nb = 0;
            Ne = 0;
            PrevRateTime = CurrentTime;
        }
        /* Analyze data */
        totCounter += (int)NumEvents;
        for(i = 0; i < (int)NumEvents; i++) {

            /* Get one event from the readout buffer */
            ret = CAEN_DGTZ_GetEventInfo(handle, buffer, BufferSize, i, &EventInfo, &EventPtr);
            if (ret) {
                ErrCode = ERR_EVENT_BUILD;
                goto QuitProgram;
            }
            /* decode the event */
            if (WDcfg.Nbit == 8) 
                ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event8);
            else
                if (BoardInfo.FamilyCode != CAEN_DGTZ_XX742_FAMILY_CODE) {
                    ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event16);
                }
                else {
                    ret = CAEN_DGTZ_DecodeEvent(handle, EventPtr, (void**)&Event742);
                    if (WDcfg.useCorrections != -1) { // if manual corrections
                        uint32_t gr;
                        for (gr = 0; gr < WDcfg.MaxGroupNumber; gr++) {
                            if ( ((WDcfg.EnableMask >> gr) & 0x1) == 0)
                                continue;
                            ApplyDataCorrection( &(X742Tables[gr]), WDcfg.DRS4Frequency, WDcfg.useCorrections, &(Event742->DataGroup[gr]));
                        }
                    }
                }
                if (ret) {
                    ErrCode = ERR_EVENT_BUILD;
                    goto QuitProgram;
                }

                /* Update Histograms */
                if (WDrun.RunHisto) {
                    for(ch=0; ch<WDcfg.Nch; ch++) {
                        int chmask = ((BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE) || (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) )? (ch/8) : ch;
                        if (!(EventInfo.ChannelMask & (1<<chmask)))
                            continue;
                        if (WDrun.Histogram[ch] == NULL) {
                            if ((WDrun.Histogram[ch] = malloc((uint64_t)(1<<WDcfg.Nbit) * sizeof(uint32_t))) == NULL) {
                                ErrCode = ERR_HISTO_MALLOC;
                                goto QuitProgram;
                            }
                            memset(WDrun.Histogram[ch], 0, (uint64_t)(1<<WDcfg.Nbit) * sizeof(uint32_t));
                        }
                        if (WDcfg.Nbit == 8)
                            for(i=0; i<(int)Event8->ChSize[ch]; i++)
                                WDrun.Histogram[ch][Event8->DataChannel[ch][i]]++;
                        else {
                            if (BoardInfo.FamilyCode != CAEN_DGTZ_XX742_FAMILY_CODE) {
                                for(i=0; i<(int)Event16->ChSize[ch]; i++)
                                    WDrun.Histogram[ch][Event16->DataChannel[ch][i]]++;
                            }
                            else {
                                printf("Can't build samples histogram for this board: it has float samples.\n");
                                WDrun.RunHisto = 0;
								WDrun.PlotType = PLOT_WAVEFORMS;
                                break;
                            }
                        }
                    }
                }

                /* Write Event data to file */
                if (WDrun.ContinuousWrite || WDrun.SingleWrite) {
                    // Note: use a thread here to allow parallel readout and file writing
                    if (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) {	
                        ret = WriteOutputFilesx742(&WDcfg, &WDrun, &EventInfo, Event742, outdir); 
                    }
                    else if (WDcfg.Nbit == 8) {
                        ret = WriteOutputFiles(&WDcfg, &WDrun, &EventInfo, Event8);
                    }
                    else {
                        ret = WriteOutputFiles(&WDcfg, &WDrun, &EventInfo, Event16);
                    }
                    if (ret) {
                        ErrCode = ERR_OUTFILE_WRITE;
                        goto QuitProgram;
                    }
                    if (WDrun.SingleWrite) {
                        sprintf(msg, "Single Event saved to output files");
                        logEntry(msg, log);
                        WDrun.SingleWrite = 0;
                    }
                }

                /* Plot Waveforms */
                if ((WDrun.ContinuousPlot || WDrun.SinglePlot) && !IsPlotterBusy()) {
                    int Ntraces = (BoardInfo.FamilyCode == CAEN_DGTZ_XX740_FAMILY_CODE) ? 8 : WDcfg.Nch;
                    if (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) Ntraces = 9;
                    if (PlotVar == NULL) {
                        int TraceLength = max(WDcfg.RecordLength, (uint32_t)(1 << WDcfg.Nbit));
                        PlotVar = OpenPlotter(WDcfg.GnuPlotPath, Ntraces, TraceLength);
                        WDrun.SetPlotOptions = 1;
                    }
                    if (PlotVar == NULL) {
                        printf("Can't open the plotter\n");
                        WDrun.ContinuousPlot = 0;
                        WDrun.SinglePlot = 0;
                    } else {
                        int Tn = 0;
                        if (WDrun.SetPlotOptions) {
                            if ((WDrun.PlotType == PLOT_WAVEFORMS) && (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE)) {
                                strcpy(PlotVar->Title, "Waveform");
                                PlotVar->Xscale = WDcfg.Ts;
                                strcpy(PlotVar->Xlabel, "ns");
                                strcpy(PlotVar->Ylabel, "ADC counts");
                                PlotVar->Yautoscale = 0;
                                PlotVar->Ymin = 0;
                                PlotVar->Ymax = (float)(1<<WDcfg.Nbit);
                                PlotVar->Xautoscale = 1;
                            } else if (WDrun.PlotType == PLOT_WAVEFORMS) {
                                strcpy(PlotVar->Title, "Waveform");
                                PlotVar->Xscale = WDcfg.Ts * WDcfg.DecimationFactor/1000;
                                strcpy(PlotVar->Xlabel, "us");
                                strcpy(PlotVar->Ylabel, "ADC counts");
                                PlotVar->Yautoscale = 0;
                                PlotVar->Ymin = 0;
                                PlotVar->Ymax = (float)(1<<WDcfg.Nbit);
                                PlotVar->Xautoscale = 1;
                            }  else if (WDrun.PlotType == PLOT_FFT) {
                                strcpy(PlotVar->Title, "FFT");
                                strcpy(PlotVar->Xlabel, "MHz");
                                strcpy(PlotVar->Ylabel, "dB");
                                PlotVar->Yautoscale = 1;
                                PlotVar->Ymin = -160;
                                PlotVar->Ymax = 0;
                                PlotVar->Xautoscale = 1;
                            } else if (WDrun.PlotType == PLOT_HISTOGRAM) {
                                PlotVar->Xscale = 1.0;
								strcpy(PlotVar->Title, "Histogram");
                                strcpy(PlotVar->Xlabel, "ADC channels");
                                strcpy(PlotVar->Ylabel, "Counts");
                                PlotVar->Yautoscale = 1;
                                PlotVar->Xautoscale = 1;
                            }
                            SetPlotOptions();
                            WDrun.SetPlotOptions = 0;
                        }
                        for(ch=0; ch<Ntraces; ch++) {
                            int absCh = WDrun.GroupPlotIndex * 8 + ch;

                            if (!((WDrun.ChannelPlotMask >> ch) & 1))
                                continue;
                            if ((BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) && ((ch != 0) && (absCh % 8) == 0)) sprintf(PlotVar->TraceName[Tn], "TR %d", (int)((absCh-1) / 16));
                            else sprintf(PlotVar->TraceName[Tn], "CH %d", absCh);
                            if (WDrun.PlotType == PLOT_WAVEFORMS) {
                                if (WDcfg.Nbit == 8) {
                                    PlotVar->TraceSize[Tn] = Event8->ChSize[absCh];
                                    memcpy(PlotVar->TraceData[Tn], Event8->DataChannel[absCh], Event8->ChSize[absCh]);
                                    PlotVar->DataType = PLOT_DATA_UINT8;
                                } else if (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) {
                                    if (Event742->GrPresent[WDrun.GroupPlotIndex]) { 
                                        PlotVar->TraceSize[Tn] = Event742->DataGroup[WDrun.GroupPlotIndex].ChSize[ch];
                                        memcpy(PlotVar->TraceData[Tn], Event742->DataGroup[WDrun.GroupPlotIndex].DataChannel[ch], Event742->DataGroup[WDrun.GroupPlotIndex].ChSize[ch] * sizeof(float));
                                        PlotVar->DataType = PLOT_DATA_FLOAT;
                                    }
                                }
                                else {
                                    PlotVar->TraceSize[Tn] = Event16->ChSize[absCh];
                                    memcpy(PlotVar->TraceData[Tn], Event16->DataChannel[absCh], Event16->ChSize[absCh] * 2);
                                    PlotVar->DataType = PLOT_DATA_UINT16;
                                }  
                            } else if (WDrun.PlotType == PLOT_FFT) {
                                int FFTns;
                                PlotVar->DataType = PLOT_DATA_DOUBLE;
                                if(WDcfg.Nbit == 8)
                                    FFTns = FFT(Event8->DataChannel[absCh], PlotVar->TraceData[Tn], Event8->ChSize[absCh], HANNING_FFT_WINDOW, SAMPLETYPE_UINT8);
                                else if (BoardInfo.FamilyCode == CAEN_DGTZ_XX742_FAMILY_CODE) {
                                    FFTns = FFT(Event742->DataGroup[WDrun.GroupPlotIndex].DataChannel[ch], PlotVar->TraceData[Tn],
                                        Event742->DataGroup[WDrun.GroupPlotIndex].ChSize[ch], HANNING_FFT_WINDOW, SAMPLETYPE_FLOAT);
                                }
                                else
                                    FFTns = FFT(Event16->DataChannel[absCh], PlotVar->TraceData[Tn], Event16->ChSize[absCh], HANNING_FFT_WINDOW, SAMPLETYPE_UINT16);
                                PlotVar->Xscale = (1000/WDcfg.Ts)/(2*FFTns);
                                PlotVar->TraceSize[Tn] = FFTns;
                            } else if (WDrun.PlotType == PLOT_HISTOGRAM) {
                                PlotVar->DataType = PLOT_DATA_UINT32;
                                strcpy(PlotVar->Title, "Histogram");
                                PlotVar->TraceSize[Tn] = 1<<WDcfg.Nbit;
                                memcpy(PlotVar->TraceData[Tn], WDrun.Histogram[absCh], (uint64_t)(1<<WDcfg.Nbit) * sizeof(uint32_t));
                            }
                            Tn++;
                            if (Tn >= MAX_NUM_TRACES)
                                break;
                        }
                        PlotVar->NumTraces = Tn;
                        if( PlotWaveforms() < 0) {
                            WDrun.ContinuousPlot = 0;
                            printf("Plot Error\n");
                        }
                        WDrun.SinglePlot = 0;
                    }
                }
        }
        
        
        if(totCounter_rdm >= maxtrig_rdm && totCounter_muon >= maxtrig_muon) {
			sprintf(msg, "Reading at %.2f MB/s (Trg Rate: %.2f Hz), random triggers = %d (%.0f%), muon triggers = %d (%.0f%)", (float)Nb/((float)ElapsedTime*1048.576f), (float)Ne*1000.0f/(float)ElapsedTime, totCounter_rdm, (float)100*totCounter_rdm/maxtrig_rdm, totCounter_muon, (float)100*totCounter_muon/maxtrig_muon);
            logEntry(msg, log);
			//printf("%d %d %d\n", totCounter, totCounter_rdm, totCounter_muon);
        	WDrun.AcqRun = 0; // disable acq.
        	//readRunFile("DAQ_RDY");
        	goto QuitProgram;

        }
    }
    ErrCode = ERR_NONE;

QuitProgram:
    if (ErrCode) {
        sprintf(msg, "\a%s", ErrMsg[ErrCode]);
        logEntry(msg, log);
#ifdef WIN32
        printf("Press a key to quit\n");
        getch();
#endif
    }

    sprintf(msg, "Triggers collected");
    logEntry(msg, log);
    
    sprintf(setrun, "STOP");
    setRunFile(setrun);

    /* stop the acquisition */
    CAEN_DGTZ_SWStopAcquisition(handle);

    /* close the plotter */
    if (PlotVar)
        ClosePlotter();

    /* close the output files and free histograms*/
    for (ch = 0; ch < WDcfg.Nch; ch++) {
        if (WDrun.fout[ch])
            fclose(WDrun.fout[ch]);
        if (WDrun.Histogram[ch])
            free(WDrun.Histogram[ch]);
    }

    /* close the device and free the buffers */
    if(Event8)
        CAEN_DGTZ_FreeEvent(handle, (void**)&Event8);
    if(Event16)
        CAEN_DGTZ_FreeEvent(handle, (void**)&Event16);
    CAEN_DGTZ_FreeReadoutBuffer(&buffer);
    CAEN_DGTZ_CloseDigitizer(handle);

    return 0;
}