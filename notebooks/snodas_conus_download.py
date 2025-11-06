# snowmodel_bounds.py
"""
    Script identifies snowmodel bounds and projection and changes input into topo_vege scripts.
"""
import xarray as xr
import os 
import rioxarray as rxr
from pyproj import CRS, Transformer
import sys
import subprocess
import numpy as np

def snodas_create_header(data_file):
    # data_file = "us_ssmv01025SlL01T0024TTNATS2020012205DP001.dat"
    header_file = data_file.replace(".dat", ".hdr")

    # ENVI header content
    header_content = """ENVI
    samples = 6935
    lines = 3351
    bands = 1
    header offset = 0
    file type = ENVI Standard
    data type = 2
    interleave = bsq
    byte order = 1
    """

    # Write the header file
    with open(header_file, "w") as hdr_file:
        hdr_file.write(header_content)

    print(f"Header file '{header_file}' created successfully.")
    return


def snodas_dat_to_nc(infile,nc_dir,download_date,gdat_translate_path):
    outfile = f"{nc_dir}SNODAS_{download_date}.nc"
    command = [
        gdat_translate_path,
        "-of", "NetCDF",
        "-a_srs", "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
        "-a_nodata", "-9999",
        "-a_ullr", "-124.73333333333333", "52.87500000000000",
        "-66.94166666666667", "24.95000000000000",
        infile,
        outfile
    ]

    # Run the command
    try:
        subprocess.run(command, check=True)
        print("Command executed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
    return outfile

def download_snodas_daily_data(water_year: str,
                               gdal_translate_fpath: str = "/glade/u/apps/derecho/24.12/spack/opt/spack/gdal/3.9.3/gcc/12.4.0/vydy/bin/gdal_translate",
                               base_out_dir: str = "/glade/campaign/ral/hap/rmower/aso/data/snodas/processing/snodas_download/data/"):
    """
    download snodas data specific to dates and basin data provided
    Input:
      cwd_ - python string of current working directory.

      scratch_dir - python string of absolute file path for scratch 
                    directory to unzip SnowModel CONUS files.
      geom_proj - geopandas object for projected basin shape.
      clip_dir - python string of relative file path to create clipped SnowModel 
                 tifs.
      aso_site_name - python string of aso site.
    Output:
    """
    # month dict
    month_dict = {
        '01': '01_Jan',
        '02': '02_Feb',
        '03': '03_Mar',
        '04': '04_Apr',
        '05': '05_May',
        '06': '06_Jun',
        '07': '07_Jul',
        '08': '08_Aug',
        '09': '09_Sep',
        '10': '10_Oct',
        '11': '11_Nov',
        '12': '12_Dec'
        
    }

    raw_dir = f'{base_out_dir}raw_conus_files/'
    nc_dir = f'{base_out_dir}nc_conus_files/'

    cwd_base = os.getcwd()

    # make directories if they do not exist.
    if not os.path.exists(raw_dir): os.makedirs(raw_dir)
    if not os.path.exists(nc_dir): os.makedirs(nc_dir)

    # create water year directory.
    nc_dir = f'{nc_dir}wy_{water_year}/'
    if not os.path.exists(nc_dir): os.makedirs(nc_dir)

    #get daily date range for water year.
    dates = np.arange(np.datetime64(f'{int(water_year)-1}-10-01'), 
                      np.datetime64(f'{int(water_year)}-09-30'), 
                      np.timedelta64(1, 'D'))
    

    # date string with hyphen
    date_str = [str(i)[0:10] for i in dates]
    # date string w/o hyphen
    date_no_hyphen = [i.replace('-','') for i in date_str]
    
    for download_date in range(0,len(date_no_hyphen)):
        download_directory = f'{raw_dir}{date_no_hyphen[download_date]}'
        print(date_no_hyphen[download_date])
        print(download_directory)
        if not os.path.exists(f'{nc_dir}SNODAS_{date_no_hyphen[download_date]}.nc'):
            try:
              tar_name = f'SNODAS_{date_no_hyphen[download_date]}.tar'
              # download snodas in directory.
              if not os.path.exists(download_directory):
                runcmd(f"wget -P {download_directory} https://noaadata.apps.nsidc.org/NOAA/G02158/masked/{date_no_hyphen[download_date][0:4]}/{month_dict[date_no_hyphen[download_date][4:6]]}/{tar_name}", verbose = False)
              # change directory
              os.chdir(download_directory)
              # unpack files.
              subprocess.run(["tar", "-xvf", tar_name])
              # iterate of unpacked files
              for file in os.listdir():
                  if 'us_ssmv11034' in file: # SWE
                    if '.dat.gz' in file:
                        # unzip file.
                        subprocess.run(["gzip", "-d", file])
                        # create header.
                        snodas_create_header(file[:-3])
                        # save netcdf.
                        file_to_save = snodas_dat_to_nc(file[:-3],nc_dir,date_no_hyphen[download_date],gdal_translate_fpath)
            
              # delete intermediate files.
              for file in os.listdir():
                os.remove(file)
            except:
              pass
        # change back to python directory since all path locations are relative
        os.chdir(cwd_base)

        #       # load netcdf.
        #       ds = xr.load_dataset(file_to_save)
        #       ds = ds.rio.write_crs('EPSG:4326')
        #       ds_clip = ds.rio.clip(geom_geog.geometry)
        #       # create xarray 
        #       da = xr.DataArray(
        #         data=ds_clip.Band1.values.reshape(1,ds_clip.Band1.shape[0],ds_clip.Band1.shape[1])/1000, # convert to meters
        #         dims=["date", "y", "x"],
        #         coords=dict(
        #             y=(["y"], ds_clip.lat.values),
        #             x=(["x"], ds_clip.lon.values),
        #             date=[np.datetime64(date_str[download_date])],
        #         ),
        #       )
        #       # name dataarray.
        #       da.name = 'SWE'
        #       da.attrs = {'SWE':'meters'}
        #       # name write crs.
        #       da = da.rio.write_crs('EPSG:4326')
        #       # reproject to shape.
        #       da = da.rio.reproject(proj_crs)
        #       # save to file.
        #       da.to_netcdf(f'{clip_dir}SNODAS_{date_no_hyphen[download_date]}.nc')
        #       # remove conus netcdf file.
        #       if deleteCONUS:
        #         os.remove(file_to_save)
        #     except:
        #         print(f'COULD NOT PROCESS {date_no_hyphen[download_date]}')

        # # delete download directory.
        # try:
        #   pass
        #   # os.removedirs(download_directory)
        # except:
        #   pass
    
    # change directory back to original.
    # os.chdir(cwd_)
    return 


def runcmd(cmd, verbose = False, *args, **kwargs):

    print(cmd)
    process = subprocess.Popen(
        cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        text = True,
        shell = True
    )
    std_out, std_err = process.communicate()
    if verbose:
        print(std_out.strip(), std_err)
    pass


if __name__ =="__main__":
    if len(sys.argv) != 2:
        print("Usage: python snodas_conus_download.py <water year>")
        sys.exit(1)
    if len(sys.argv) == 2:
        water_year = sys.argv[1]
        download_snodas_daily_data(water_year)




